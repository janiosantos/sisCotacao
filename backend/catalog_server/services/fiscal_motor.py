"""Motor de regras fiscais (FASE 3).

Componentes:
- `FiscalContext`        : contexto fiscal da operação (empresa, produto, cliente,
                           valores, data).
- `resolver(contexto)`   : FiscalRuleEngine → `FiscalResult` (CFOP, CST/CSOSN,
                           ICMS, ST, PIS, COFINS, IBS/CBS, bases/valores e
                           MEMÓRIA DE CÁLCULO). Determinístico: mesmas entradas +
                           mesma versão de regras = mesmo resultado.
- `validar(contexto, r)` : FiscalValidator (ERROR bloqueia; WARNING/INFO permitem).

Regras de decisão (não inventar):
1. Se houver regra de contexto na matriz (`fiscal_regra`) com versão vigente na
   data → usa a matriz (origem = 'regra', com memória da versão/fonte).
2. Senão, se o produto tem parametrização fiscal (`fiscal_config`) → usa a
   configuração do produto, com WARNING "sem regra de contexto".
3. Senão → `FISCAL_RULE_NOT_FOUND` (sem CFOP/CST/CSOSN inventados) e ERROR que
   impede a emissão.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from catalog_server.db import system_conn
from catalog_server.services import fiscal_engine, fiscal_regras

# Camada PIS/COFINS — semântica de CST (NECESSITA VALIDAÇÃO):
# CSTs que NÃO destacam PIS/COFINS na operação (alíquota zero, monofásico,
# isenção, sem incidência, suspensão, ST, crédito presumido, outros).
CST_PIS_COFINS_NAO_DESTACA = frozenset({
    "04", "05", "06", "07", "08", "09", "49", "50", "51", "52", "53", "54", "55", "98", "99",
})
CST_PIS_COFINS_OBS = {
    "01": "Operação tributável - alíquota básica",
    "02": "Operação tributável - alíquota diferenciada",
    "03": "Operação tributável - por unidade",
    "04": "Alíquota zero / monofásico",
    "05": "Substituição tributária (PIS/COFINS)",
    "06": "Alíquota zero com ST",
    "07": "Isenta da contribuição",
    "08": "Sem incidência da contribuição",
    "09": "Suspensão",
    "49": "Outras operações de saída",
    "50": "Direito a crédito",
    "51": "Sem direito a crédito",
    "52": "Crédito presumido",
    "98": "Outras",
    "99": "Outras operações",
}


def calcular_piscofins(regime: str, cst: str, base: float, aliquota: float, tributo: str = "PIS") -> dict:
    """Camada independente de PIS/COFINS.

    Regra: Simples Nacional não destaca PIS/COFINS (DAS). No Regime Normal,
    apenas CSTs tributáveis (01/02/03) destacam; monofásico/alíquota
    zero/isenção/ST etc. geram valor zero.
    """
    if regime == "simples_nacional":
        return {"cst": cst, "base": round(base, 2), "aliquota": 0.0, "valor": 0.0,
                "destacado": False, "observacao": "Simples Nacional: PIS/COFINS no DAS (não destacado)"}
    if not cst:
        return {"cst": "", "base": round(base, 2), "aliquota": round(aliquota, 4), "valor": 0.0,
                "destacado": False, "observacao": f"{tributo}: CST não informado — não destacado"}
    if cst in CST_PIS_COFINS_NAO_DESTACA:
        return {"cst": cst, "base": round(base, 2), "aliquota": round(aliquota, 4), "valor": 0.0,
                "destacado": False,
                "observacao": f"{tributo}: CST {cst} — {CST_PIS_COFINS_OBS.get(cst, 'não destacado')}"}
    valor = round(base * aliquota / 100, 2)
    return {"cst": cst, "base": round(base, 2), "aliquota": round(aliquota, 4), "valor": valor,
            "destacado": True,
            "observacao": f"{tributo}: CST {cst} — {CST_PIS_COFINS_OBS.get(cst, 'tributável')}"}


def _vigente(inicio: str | None, fim: str | None, data: str) -> bool:
    if not inicio:
        return False
    if data < inicio:
        return False
    if fim and data > fim:
        return False
    return True


def calcular_ibs_cbs(
    regime: str,
    cst: str,
    base: float,
    aliquota: float,
    vigente: bool,
    tributo: str,
) -> dict:
    """IBS/CBS — transição da Reforma Tributária (NECESSITA VALIDAÇÃO).

    Parâmetros com vigência (alíquotas no emitente/regra, nunca constantes).
    Sem alíquota parametrizada e vigente → valor 0 com observação (não inventar).
    """
    if not vigente:
        return {"cst": cst, "base": round(base, 2), "aliquota": round(aliquota, 4), "valor": 0.0,
                "vigente": False, "observacao": f"{tributo}: fora da vigência parametrizada"}
    if aliquota <= 0:
        return {"cst": cst, "base": round(base, 2), "aliquota": 0.0, "valor": 0.0,
                "vigente": True, "observacao": f"{tributo}: vigente, mas alíquota não parametrizada (validar)"}
    valor = round(base * aliquota / 100, 2)
    return {"cst": cst, "base": round(base, 2), "aliquota": round(aliquota, 4), "valor": valor,
            "vigente": True, "observacao": f"{tributo}: transição 2026 (validar)"}


@dataclass
class FiscalContext:
    operacao: str = "venda"
    variante_id: int | None = None
    cliente_id: int | None = None
    uf_destino: str | None = None
    tipo_cliente: str | None = None      # PF | PJ
    contribuinte: str | None = None      # contribuinte | nao_contribuinte
    ie: str | None = None
    finalidade: str = "normal"
    modelo_documento: str | None = None  # 55 | 65
    data: str | None = None
    quantidade: float = 1.0
    valor_unitario: float = 0.0
    desconto: float = 0.0
    frete: float = 0.0
    seguro: float = 0.0
    outras_despesas: float = 0.0

    def consulta_matriz(self) -> dict:
        return {
            "regime": None,  # preenchido após carregar emitente
            "uf_origem": None,
            "uf_destino": self.uf_destino,
            "tipo_cliente": self.tipo_cliente,
            "contribuinte": self.contribuinte,
            "finalidade": self.finalidade,
            "modelo_documento": self.modelo_documento,
            "natureza_operacao": self.operacao,
        }


def montar_contexto(dados: dict) -> FiscalContext:
    """Constrói o contexto a partir de um dict; completa dados do cliente se informado."""
    ctx = FiscalContext(
        operacao=dados.get("operacao", "venda"),
        variante_id=dados.get("variante_id") or dados.get("produto_id"),
        cliente_id=dados.get("cliente_id"),
        uf_destino=(dados.get("uf_destino") or "").strip().upper() or None,
        tipo_cliente=dados.get("tipo_cliente"),
        contribuinte=dados.get("contribuinte"),
        ie=dados.get("ie"),
        finalidade=dados.get("finalidade", "normal"),
        modelo_documento=dados.get("modelo_documento"),
        data=dados.get("data"),
        quantidade=float(dados.get("quantidade") or 1),
        valor_unitario=float(dados.get("valor_unitario") or 0),
        desconto=float(dados.get("desconto") or 0),
        frete=float(dados.get("frete") or 0),
        seguro=float(dados.get("seguro") or 0),
        outras_despesas=float(dados.get("outras_despesas") or 0),
    )
    if ctx.cliente_id:
        with system_conn() as conn:
            cli = conn.execute(
                "SELECT tipo_pessoa, uf, contribuinte, ie FROM clientes WHERE id=?",
                (ctx.cliente_id,),
            ).fetchone()
        if cli:
            if not ctx.tipo_cliente:
                ctx.tipo_cliente = "PJ" if cli["tipo_pessoa"] == "j" else "PF"
            if not ctx.uf_destino and cli["uf"]:
                ctx.uf_destino = cli["uf"].strip().upper()
            if not ctx.contribuinte:
                ctx.contribuinte = cli["contribuinte"] or None
            if not ctx.ie and cli["ie"]:
                ctx.ie = cli["ie"]
    return ctx


def resolver(contexto: FiscalContext) -> dict:
    """FiscalRuleEngine.resolve(contexto) → FiscalResult (com memória de cálculo)."""
    resultado: dict = {
        "status": "ok",
        "operacao": contexto.operacao,
        "data": contexto.data or date.today().isoformat(),
        "tipo_cliente": contexto.tipo_cliente,
        "contribuinte": contexto.contribuinte,
        "uf_destino": contexto.uf_destino,
        "finalidade": contexto.finalidade,
        "modelo_documento": contexto.modelo_documento,
        "variante_id": contexto.variante_id,
        "quantidade": contexto.quantidade,
        "valor_unitario": contexto.valor_unitario,
        # Classificação (preenchido abaixo)
        "ncm": "", "cest": "", "cfop": "", "origem": 0,
        "cst_icms": "", "csosn": "", "cst_pis": "", "cst_cofins": "",
        "cst_ibs": "", "cst_cbs": "",
        # ICMS
        "aliquota_icms": 0.0, "base_icms": 0.0, "valor_icms": 0.0,
        # ST
        "modalidade_st": "", "base_icms_st": 0.0, "aliquota_icms_st": 0.0, "valor_icms_st": 0.0,
        # PIS/COFINS
        "aliquota_pis": 0.0, "valor_pis": 0.0, "aliquota_cofins": 0.0, "valor_cofins": 0.0,
        # IBS/CBS (parâmetros — cálculo na fase IBS/CBS)
        "aliquota_ibs": 0.0, "valor_ibs": 0.0, "aliquota_cbs": 0.0, "valor_cbs": 0.0,
        "ibs_parametrizado": False,
        # Memória de cálculo
        "memoria": {
            "origem": "fiscal_rule_not_found",
            "regra_id": None, "regra_nome": None, "versao": None,
            "fonte": None, "data_vigencia_inicio": None, "data_vigencia_fim": None,
            "observacao": None,
        },
        "problemas": [],
        "status_validacao": "ok",
    }

    # Fiscal base (parametrização do produto)
    fiscal = fiscal_engine.calculate(
        contexto.variante_id,
        operacao=contexto.operacao,
        uf_dest=contexto.uf_destino,
        tipo_cliente=contexto.tipo_cliente,
        contribuinte=contexto.contribuinte,
    ) if contexto.variante_id else None

    if fiscal is None:
        resultado["status"] = "FISCAL_RULE_NOT_FOUND"
        resultado["problemas"] = [{"tipo": "ERROR", "campo": "regra",
                                   "mensagem": "Produto sem parametrização fiscal (NCM/CST/CSOSN). Sem regra aplicável — emissão bloqueada."}]
        resultado["status_validacao"] = "erro"
        return resultado

    resultado["regime"] = fiscal["regime"]
    resultado["ncm"] = fiscal["ncm"]
    resultado["cest"] = fiscal["cest"]
    resultado["origem"] = fiscal["origem"]
    resultado["aliquota_icms"] = fiscal["aliquota_icms"]
    resultado["aliquota_pis"] = fiscal["aliquota_pis"]
    resultado["aliquota_cofins"] = fiscal["aliquota_cofins"]
    resultado["aliquota_ibs"] = fiscal["transicao"]["aliquota_ibs"]
    resultado["aliquota_cbs"] = fiscal["transicao"]["aliquota_cbs"]
    resultado["ibs_parametrizado"] = bool(fiscal["transicao"]["aliquota_ibs"] or fiscal["transicao"]["aliquota_cbs"])

    # Matriz de contexto (vigente na data) — COMPOSIÇÃO operação × produto
    consulta = contexto.consulta_matriz()
    consulta["regime"] = fiscal["regime"]
    consulta["uf_origem"] = fiscal["uf_origem"]
    consulta["ncm"] = fiscal["ncm"]
    consulta["cest"] = fiscal["cest"]
    consulta["origem"] = fiscal["origem"]
    regra_op = fiscal_regras.buscar_regra(consulta, data=resultado["data"], dimensao="operacao")
    regra_prod = fiscal_regras.buscar_regra(consulta, data=resultado["data"], dimensao="produto")

    # Resolve classificação: regra de operação > regra de produto (ST) > parametrização
    def _val(regra, campo, padrao):
        return (regra or {}).get(campo) or padrao

    resultado["cfop"] = _val(regra_op, "cfop", fiscal["cfop"])
    # PIS/COFINS: CST é atributo do PRODUTO (monofásico/zero/isenção);
    # a regra de operação é só fallback.
    resultado["cst_pis"] = _val(regra_prod, "cst_pis", fiscal["cst_pis"]) or _val(regra_op, "cst_pis", "")
    resultado["cst_cofins"] = _val(regra_prod, "cst_cofins", fiscal["cst_cofins"]) or _val(regra_op, "cst_cofins", "")
    resultado["cst_ibs"] = _val(regra_prod, "cst_ibs", _val(regra_op, "cst_ibs", ""))
    resultado["cst_cbs"] = _val(regra_prod, "cst_cbs", _val(regra_op, "cst_cbs", ""))
    # CST/CSOSN: regra de produto (ST) tem prioridade sobre a de operação
    resultado["cst_icms"] = _val(regra_prod, "cst_icms", _val(regra_op, "cst_icms", fiscal["cst_icms"]))
    resultado["csosn"] = _val(regra_prod, "csosn", _val(regra_op, "csosn", fiscal["csosn"]))
    # Coerência regime × CST/CSOSN: Simples usa CSOSN; Regime Normal usa CST
    if fiscal["regime"] == "simples_nacional":
        resultado["cst_icms"] = ""
    else:
        resultado["csosn"] = ""

    # Alíquotas/ST: regra de produto > regra de operação > configuração
    for campo in ("aliquota_icms", "aliquota_icms_st", "mva", "base_reducao", "aliquota_pis", "aliquota_cofins", "modalidade_st",
                  "aliquota_ibs", "aliquota_cbs"):
        v = _val(regra_prod, campo, _val(regra_op, campo, fiscal.get(campo, 0) if campo in fiscal else fiscal["icms_st"].get(campo)))
        if v is not None:
            resultado[campo] = v

    # Memória de cálculo (operação + produto)
    if regra_op:
        resultado["memoria"].update({
            "origem": "regra",
            "regra_id": regra_op.get("id"),
            "regra_nome": regra_op.get("nome"),
            "versao": (regra_op.get("versao") or {}).get("versao"),
            "fonte": (regra_op.get("versao") or {}).get("fonte"),
            "data_vigencia_inicio": (regra_op.get("versao") or {}).get("data_inicio"),
            "data_vigencia_fim": (regra_op.get("versao") or {}).get("data_fim"),
        })
    else:
        resultado["memoria"].update({
            "origem": "config",
            "observacao": "Sem regra de contexto na matriz — usando parametrização do produto.",
        })
        resultado["problemas"].append({"tipo": "WARNING", "campo": "regra",
                                       "mensagem": "Sem regra de operação na matriz; usando configuração do produto."})
    resultado["memoria_produto"] = None
    if regra_prod:
        resultado["memoria_produto"] = {
            "regra_id": regra_prod.get("id"),
            "regra_nome": regra_prod.get("nome"),
            "versao": (regra_prod.get("versao") or {}).get("versao"),
            "fonte": (regra_prod.get("versao") or {}).get("fonte"),
        }
        if resultado["memoria"]["origem"] != "regra":
            resultado["problemas"].append({"tipo": "INFO", "campo": "regra_produto",
                                           "mensagem": "Regra de produto (ST) aplicada: " + str(regra_prod.get("nome"))})

    # DIFAL (venda interestadual)
    resultado["difal"] = {
        "aplica": fiscal["difal"]["aplica"],
        "uf_origem": fiscal["difal"]["uf_origem"],
        "uf_destino": fiscal["difal"].get("uf_dest"),
        "aliquota_interestadual": fiscal["difal"]["aliquota_interestadual"],
        "aliquota_fecp": fiscal["difal"]["aliquota_fecp"],
    }

    # Bases e valores
    valor_total = round(contexto.quantidade * contexto.valor_unitario, 2)
    base = round(max(0.0, valor_total - contexto.desconto + contexto.frete + contexto.seguro + contexto.outras_despesas), 2)
    resultado["base_icms"] = base
    if fiscal["regime"] != "simples_nacional":
        resultado["valor_icms"] = round(base * resultado["aliquota_icms"] / 100, 2)
    else:
        resultado["valor_icms"] = 0.0  # Simples: ICMS não destacado

    # ICMS-ST
    icms_st = fiscal["icms_st"]
    aplica_st = bool(icms_st.get("aplica")) or bool(resultado.get("modalidade_st"))
    resultado["aliquota_icms_st"] = resultado.get("aliquota_icms_st") or float(icms_st.get("aliquota") or 0)
    mva = float(resultado.get("mva") or icms_st.get("mva") or 0)
    reducao = float(resultado.get("base_reducao") or icms_st.get("base_reducao") or 0)
    if aplica_st:
        base_st = base * (1 + mva / 100) * (1 - reducao / 100)
        resultado["base_icms_st"] = round(base_st, 2)
        st_devido = base_st * resultado["aliquota_icms_st"] / 100
        resultado["valor_icms_st"] = round(max(0.0, st_devido - resultado["valor_icms"]), 2)

    # PIS/COFINS (camada independente)
    pis = calcular_piscofins(fiscal["regime"], resultado["cst_pis"], base, resultado["aliquota_pis"], "PIS")
    cofins = calcular_piscofins(fiscal["regime"], resultado["cst_cofins"], base, resultado["aliquota_cofins"], "COFINS")
    resultado["valor_pis"] = pis["valor"]
    resultado["valor_cofins"] = cofins["valor"]
    resultado["piscofins"] = {"pis": pis, "cofins": cofins}

    # IBS/CBS (transição da Reforma Tributária — NECESSITA VALIDAÇÃO)
    trans = fiscal["transicao"]
    data = resultado["data"]
    ibs_vig = _vigente(trans["ibs_vigencia"]["inicio"], trans["ibs_vigencia"]["fim"], data)
    cbs_vig = _vigente(trans["cbs_vigencia"]["inicio"], trans["cbs_vigencia"]["fim"], data)
    aliq_ibs = resultado.get("aliquota_ibs") or trans["aliquota_ibs"]
    aliq_cbs = resultado.get("aliquota_cbs") or trans["aliquota_cbs"]
    ibs = calcular_ibs_cbs(fiscal["regime"], resultado["cst_ibs"], base, aliq_ibs, ibs_vig, "IBS")
    cbs = calcular_ibs_cbs(fiscal["regime"], resultado["cst_cbs"], base, aliq_cbs, cbs_vig, "CBS")
    resultado["valor_ibs"] = ibs["valor"]
    resultado["valor_cbs"] = cbs["valor"]
    resultado["aliquota_ibs"] = ibs["aliquota"]
    resultado["aliquota_cbs"] = cbs["aliquota"]
    resultado["ibs_cbs"] = {"ibs": ibs, "cbs": cbs}

    # Árvore de decisão ("por que essa regra?")
    resultado["decisao"] = [
        {"passo": "Contexto",
         "detalhe": f"Regime {fiscal['regime']} · Origem {fiscal['uf_origem'] or '—'} → Destino {contexto.uf_destino or '—'}"
                    f" · Cliente {contexto.tipo_cliente or '—'} ({contexto.contribuinte or 'contribuinte não informado'})"
                    f" · Operação {contexto.operacao} · Modelo {contexto.modelo_documento or '—'} · Data {resultado['data']}"},
        {"passo": "Produto",
         "detalhe": f"NCM {resultado['ncm']} · CEST {resultado['cest'] or '—'} · Origem {resultado['origem']}"},
        {"passo": "Regra de operação",
         "detalhe": (f"{regra_op['nome']} (versão {regra_op['versao']['versao']}, fonte {regra_op['versao']['fonte'] or '—'})"
                     if regra_op else "Nenhuma regra de operação — usou a configuração do produto")},
        {"passo": "Regra de produto",
         "detalhe": (f"{regra_prod['nome']} (versão {regra_prod['versao']['versao']}, fonte {regra_prod['versao']['fonte'] or '—'})"
                     if regra_prod else "Nenhuma")},
        {"passo": "Classificação",
         "detalhe": f"CFOP {resultado['cfop']} · CST/CSOSN {resultado['cst_icms'] or resultado['csosn'] or '—'}"},
        {"passo": "ICMS",
         "detalhe": f"Base {resultado['base_icms']} · Alíq. {resultado['aliquota_icms']}% · Valor {resultado['valor_icms']}"},
        {"passo": "ICMS-ST",
         "detalhe": (f"Aplica (MVA {mva}%, base {resultado['base_icms_st']}, valor {resultado['valor_icms_st']})"
                     if aplica_st else "Não aplica")},
        {"passo": "PIS/COFINS",
         "detalhe": f"PIS {resultado['valor_pis']} · COFINS {resultado['valor_cofins']}"},
        {"passo": "IBS/CBS",
         "detalhe": f"IBS {resultado['valor_ibs']} (vigente {ibs_vig}) · CBS {resultado['valor_cbs']} (vigente {cbs_vig})"},
    ]

    # Validação
    resultado["problemas"] += validar(contexto, resultado)
    resultado["status_validacao"] = "erro" if any(p["tipo"] == "ERROR" for p in resultado["problemas"]) else "ok"
    return resultado


def validar(contexto: FiscalContext, resultado: dict) -> list[dict]:
    """FiscalValidator — ERROR bloqueia; WARNING/INFO permitem."""
    probs: list[dict] = []
    regime = resultado.get("regime")

    if not resultado.get("ncm"):
        probs.append({"tipo": "ERROR", "campo": "ncm", "mensagem": "NCM ausente no produto."})
    if not resultado.get("cfop"):
        probs.append({"tipo": "ERROR", "campo": "cfop", "mensagem": "CFOP indefinido para a operação."})
    if regime == "simples_nacional" and not resultado.get("csosn"):
        probs.append({"tipo": "ERROR", "campo": "csosn", "mensagem": "Regime Simples Nacional exige CSOSN."})
    if regime and regime != "simples_nacional" and not resultado.get("cst_icms"):
        probs.append({"tipo": "ERROR", "campo": "cst_icms", "mensagem": "Regime normal exige CST de ICMS."})
    if contexto.operacao == "venda" and not contexto.uf_destino:
        probs.append({"tipo": "ERROR", "campo": "uf_destino", "mensagem": "UF de destino obrigatória na venda."})
    if contexto.tipo_cliente not in ("PF", "PJ"):
        probs.append({"tipo": "WARNING", "campo": "tipo_cliente", "mensagem": "Tipo de cliente (PF/PJ) não informado."})
    if contexto.contribuinte not in ("contribuinte", "nao_contribuinte"):
        probs.append({"tipo": "WARNING", "campo": "contribuinte", "mensagem": "Condição de contribuinte não informada."})
    if not contexto.modelo_documento:
        probs.append({"tipo": "WARNING", "campo": "modelo_documento", "mensagem": "Modelo de documento (NF-e 55 / NFC-e 65) não informado."})
    if resultado.get("aliquota_icms") is None or resultado["aliquota_icms"] < 0:
        probs.append({"tipo": "ERROR", "campo": "aliquota_icms", "mensagem": "Alíquota de ICMS inválida."})
    return probs


def simular(dados: dict) -> dict:
    """Simula uma operação (produto + cliente + operação + data) → resultado + validação."""
    ctx = montar_contexto(dados)
    return resolver(ctx)
