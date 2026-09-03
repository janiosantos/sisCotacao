"""Motor de Precificação.

Consome o Motor de Custo (`custo_engine.calcular_custo`) — que por sua vez
consome o Motor Fiscal — e aplica os componentes de venda para calcular o preço
mínimo e o preço sugerido de uma variante.

Regras (documentadas):
- Custo líquido vem do módulo de Custo (tributos/créditos já tratados no Fiscal).
- Preço pelo DIVISOR (metodologia Sebrae da planilha de referência):
      preco = custo_formacao / (1 − percentuais sobre a venda)
- Preço por MARKUP (sobre o custo), quando informado no lugar da margem:
      preco = custo_liquido × (1 + markup / 100)
- Preço mínimo = cobre custo + despesas variáveis (margem zero):
      preco_minimo = custo_liquido / (1 − (despesas + comissão + taxas) / 100)

Margem e markup são mutuamente exclusivos (margem tem prioridade). O canal pode
selecionar a tabela de preço correspondente (varejo/atacado/contrato/promocional)
para herdar margem_padrao/markup.

Este módulo NÃO recalcula tributos nem créditos (responsabilidade do Fiscal).
"""
from __future__ import annotations

from catalog_server.db import system_conn
from catalog_server.services import custo_engine
from catalog_server.services import precificacao_config
from catalog_server.services import precificacao_metodologia


def _tabela_do_canal(canal: str | None, tabela_id: int | None) -> dict | None:
    with system_conn() as conn:
        if tabela_id:
            row = conn.execute(
                "SELECT * FROM tabelas_preco WHERE id=? AND ativo=1", (tabela_id,)
            ).fetchone()
        elif canal:
            row = conn.execute(
                "SELECT * FROM tabelas_preco WHERE tipo=? AND ativo=1 ORDER BY id LIMIT 1",
                (canal,),
            ).fetchone()
        else:
            return None
        return dict(row) if row else None


def _explicacao_regra(regra: dict) -> str:
    partes: list[str] = []
    if regra.get("canal"):
        partes.append(f"canal {regra['canal']}")
    if regra.get("cliente_id"):
        partes.append(f"cliente {regra['cliente_id']}")
    if regra.get("segmento"):
        partes.append(f"segmento {regra['segmento']}")
    if regra.get("quantidade_min") is not None:
        partes.append(f"qtd ≥ {regra['quantidade_min']}")
    if regra.get("preco") is not None:
        base = "preço fixo"
    else:
        base = f"desconto {regra.get('desconto_pct')}%"
    contexto = f" [{', '.join(partes)}]" if partes else " [geral]"
    return f"Regra #{regra['id']} (prio {regra.get('prioridade')}): {base}{contexto}"


def calcular_preco(
    produto_id: int,
    canal: str | None = None,
    margem: float | None = None,
    markup: float | None = None,
    comissao: float = 0.0,
    despesas: float = 0.0,
    taxas: float = 0.0,
    tabela_id: int | None = None,
    fornecedor_id: int | None = None,
    embalagem_unitaria: float = 0.0,
    frete_unitario: float = 0.0,
    frete_pct: float = 0.0,
    cartao_pct: float | None = None,
    impostos_pct: float | None = None,
    despesas_fixas_pct: float | None = None,
    usar_referencia_atividade: bool | None = None,
    cenario_tributario: str | None = None,
    reforma_tributaria_pct: float | None = None,
    competencia_value: str | None = None,
    incluir_despesas_variaveis_rateadas: bool = False,
) -> dict:
    canal = canal if canal in ("varejo", "atacado", "contrato", "promocional") else None
    custo = custo_engine.calcular_custo(produto_id, fornecedor_id=fornecedor_id)
    tabela = _tabela_do_canal(canal, tabela_id)
    config = precificacao_config.obter()
    apuracao = None
    competencia_configurada = config.get("competencia_precificacao") if config.get("usar_competencia_aprovada", True) else None
    competencia_usada = competencia_value or competencia_configurada
    incluir_rateio_config = bool(config.get("incluir_despesas_variaveis_rateadas"))
    if competencia_usada or incluir_despesas_variaveis_rateadas or incluir_rateio_config:
        from catalog_server.services import classificacao_financeira

        apuracao = classificacao_financeira.apuracao_para_precificacao(competencia_usada)
    fixas_origem = "parametro"
    fixas_alerta = None
    if despesas_fixas_pct is None and apuracao and (competencia_value or competencia_configurada or usar_referencia_atividade is False):
        despesas_fixas = float(apuracao.get("despesa_fixa_pct") or 0)
        fixas_origem = f"competencia:{apuracao['competencia']}"
    elif despesas_fixas_pct is None:
        if despesas:
            despesas_fixas = float(despesas)
        else:
            despesas_fixas, fixas_origem, fixas_alerta = precificacao_config.despesas_fixas_pct(
                config, usar_referencia_atividade
            )
    else:
        despesas_fixas = float(despesas_fixas_pct)
    despesas_variaveis_rateadas = 0.0
    variaveis_origem = "nao_incluidas"
    variaveis_alerta = None
    if incluir_despesas_variaveis_rateadas or incluir_rateio_config:
        if apuracao and apuracao.get("despesa_variavel_pct") is not None:
            despesas_variaveis_rateadas = float(apuracao["despesa_variavel_pct"] or 0)
            variaveis_origem = f"competencia:{apuracao['competencia']}"
        else:
            variaveis_origem = "sem_competencia_aprovada"
            variaveis_alerta = "Despesas variáveis rateadas solicitadas, mas não há competência aprovada ou fechada."
    cartao = float(cartao_pct) if cartao_pct is not None else (float(taxas or 0) or float(config.get("taxa_cartao_pct") or 0))
    impostos = float(impostos_pct) if impostos_pct is not None else float(config.get("impostos_atual_pct") or 0)
    cenario = cenario_tributario or str(config.get("cenario_tributario") or "atual")
    reforma = (
        float(reforma_tributaria_pct)
        if reforma_tributaria_pct is not None
        else float(config.get("reforma_tributaria_pct") or 0)
    )
    margem_final = float(margem) if margem is not None else float((tabela or {}).get("margem_padrao") or 0)
    markup_final = float(markup) if markup is not None else float((tabela or {}).get("markup") or 0)
    # A coluna legada de markup continua disponível, mas a metodologia padrão
    # é o divisor. Só usa markup sobre custo quando a tabela o declara.
    metodo_tabela = str((tabela or {}).get("metodologia") or "divisor")
    if margem is None and markup is not None and markup > 0:
        metodo_tabela = "markup_custo"
    base = {
        "produto_id": produto_id,
        "canal": canal,
        "tabela_id": tabela["id"] if tabela else (tabela_id or None),
        "tabela_nome": (tabela.get("nome") if tabela else None),
        "custo_base": custo.get("custo_base"),
        "custo_liquido": custo.get("custo_liquido"),
        "regime": custo.get("regime"),
        "despesas_pct": {"comissao": max(0.0, float(comissao or 0)), "despesas": despesas_fixas, "despesas_variaveis_rateadas": despesas_variaveis_rateadas, "taxas": cartao, "total": 0.0},
        "configuracao": {
            "atividade": config.get("atividade"),
            "atividade_nome": (config.get("referencia_atividade") or {}).get("nome"),
            "despesas_fixas_origem": fixas_origem,
            "despesa_fixa_real_pct": config.get("despesa_fixa_real_pct"),
            "despesa_variavel_real_pct": config.get("despesa_variavel_real_pct"),
            "despesas_variaveis_origem": variaveis_origem,
            "competencia": apuracao.get("competencia") if apuracao else competencia_value,
        },
        "metodologia": "divisor" if metodo_tabela != "markup_custo" else "markup_custo",
        "cenario_tributario": cenario,
        "preco_minimo": None,
        "preco_sugerido": None,
        "margem_efetiva_pct": None,
        "markup_efetivo_pct": None,
        "observacao": None,
        "fiscal": custo.get("fiscal"),
    }
    if custo.get("custo_liquido") is None:
        base["observacao"] = "Sem custo de aquisição definido."
        return base

    custo_liq = float(custo["custo_liquido"])
    if metodo_tabela == "markup_custo" and markup_final > 0:
        preco = round((custo_liq + float(embalagem_unitaria or 0) + float(frete_unitario or 0)) * (1 + markup_final / 100), 2)
        base.update({
            "metodologia": "markup_custo",
            "preco_sugerido": preco,
            "preco_minimo": round(custo_liq + float(embalagem_unitaria or 0) + float(frete_unitario or 0), 2),
            "margem_efetiva_pct": round((preco - custo_liq) / preco * 100, 2) if preco else None,
            "markup_efetivo_pct": markup_final,
            "observacao": "Markup sobre o custo (compatibilidade legada)",
        })
        return base

    try:
        memoria = precificacao_metodologia.calcular(
            custo_liq,
            embalagem_unitaria=embalagem_unitaria,
            frete_unitario=frete_unitario,
            frete_pct=frete_pct,
            cartao_pct=cartao,
            impostos_pct=impostos if cenario == "atual" else 0,
            comissao_pct=comissao,
            despesas_variaveis_pct=despesas_variaveis_rateadas,
            despesas_fixas_pct=despesas_fixas,
            margem_pct=margem_final,
            cenario_tributario=cenario,
            reforma_tributaria_pct=reforma,
        )
    except ValueError as exc:
        base["observacao"] = str(exc)
        return base
    base.update({
        "metodologia_memoria": memoria,
        "preco_minimo": memoria.get("preco_minimo"),
        "preco_sugerido": memoria.get("preco_sugerido"),
        "margem_efetiva_pct": memoria.get("margem_efetiva_pct"),
        "markup_efetivo_pct": memoria.get("markup_efetivo_pct"),
        "despesas_pct": {
            "comissao": comissao,
            "despesas_variaveis_rateadas": despesas_variaveis_rateadas,
            "despesas": despesas_fixas,
            "taxas": cartao,
            "total": memoria["percentuais"]["custos_percentuais"],
        },
        "observacao": "Markup divisor: custo de formação ÷ (1 − percentuais sobre a venda)",
    })
    if fixas_alerta:
        base["metodologia_memoria"]["alertas"].append(fixas_alerta)
    if variaveis_alerta:
        base["metodologia_memoria"]["alertas"].append(variaveis_alerta)
    if memoria.get("alertas"):
        base["observacao"] = "; ".join(memoria["alertas"])
    return base


def preco_efetivo(
    produto_id: int,
    canal: str = "varejo",
    cliente_id: int | None = None,
    segmento: str | None = None,
    quantidade: float | None = None,
) -> dict:
    """Preço efetivo de venda: regra de preço (MDM-007) → tabela do canal → motor (sugerido) → preço base."""
    canal = canal if canal in ("varejo", "atacado", "contrato", "promocional") else "varejo"

    from catalog_server.services import preco_regra as preco_regra_svc

    regra = preco_regra_svc.resolver(
        produto_id, canal=canal, cliente_id=cliente_id, segmento=segmento, quantidade=quantidade
    )
    if regra:
        base = 0.0
        if regra.get("preco") is not None:
            base = float(regra["preco"])
        else:
            with system_conn() as conn:
                row = conn.execute(
                    "SELECT preco FROM produtos_cadastro WHERE id=?", (produto_id,)
                ).fetchone()
            base = float(row["preco"]) if row and row["preco"] else 0.0
            desconto = float(regra.get("desconto_pct") or 0)
            base = round(base * (1 - desconto / 100), 2)
        resp = {
            "produto_id": produto_id, "canal": canal,
            "preco": base, "origem": "regra",
            "regra_id": regra["id"],
            "prioridade": regra.get("prioridade"),
            "explicacao": _explicacao_regra(regra),
        }
        if regra.get("margem_minima_pct") is not None:
            custo = custo_engine.calcular_custo(produto_id)
            custo_liq = float(custo.get("custo_liquido") or 0)
            resp["custo_liquido"] = custo_liq
            if custo_liq > 0:
                margem_real = round((base - custo_liq) / base * 100, 2) if base > 0 else None
                resp["margem_real_pct"] = margem_real
                resp["margem_minima_pct"] = float(regra["margem_minima_pct"])
                resp["abaixo_da_margem_minima"] = bool(
                    margem_real is not None and margem_real < float(regra["margem_minima_pct"])
                )
        return resp

    tabela = _tabela_do_canal(canal, None)
    if tabela:
        with system_conn() as conn:
            row = conn.execute(
                "SELECT preco FROM tabela_preco_itens"
                " WHERE tabela_id=? AND produto_id=? AND ativo=1",
                (tabela["id"], produto_id),
            ).fetchone()
        if row and row["preco"]:
            return {
                "produto_id": produto_id, "canal": canal,
                "preco": float(row["preco"]), "origem": "tabela",
                "tabela_id": tabela["id"],
            }
    calc = calcular_preco(produto_id, canal=canal)
    if calc.get("preco_sugerido") is not None:
        return {
            "produto_id": produto_id, "canal": canal,
            "preco": calc["preco_sugerido"], "origem": "motor",
            "tabela_id": calc.get("tabela_id"),
            "custo_liquido": calc.get("custo_liquido"),
        }
    with system_conn() as conn:
        row = conn.execute("SELECT preco FROM produtos_cadastro WHERE id=?", (produto_id,)).fetchone()
    preco = float(row["preco"]) if row and row["preco"] else 0.0
    return {"produto_id": produto_id, "canal": canal, "preco": preco, "origem": "base"}


def previa_reajuste(
    tabela_id: int,
    margem: float | None = None,
    markup: float | None = None,
    termo: str | None = None,
    limit: int = 500,
) -> dict:
    """Prévia do reajuste em lote: calcula o preço sugerido (motor) sem gravar."""
    tabela = _tabela_do_canal(None, tabela_id) or {}
    m = margem if margem is not None else float(tabela.get("margem_padrao") or 0)
    mk = markup if markup is not None else float(tabela.get("markup") or 0)

    sql = """
        SELECT p.id, p.sku, p.preco AS preco_atual, p.nome AS produto_nome, p.marca
        FROM produtos_cadastro p
        WHERE p.ativo = 1
          AND (EXISTS (SELECT 1 FROM fornecedor_preco fp
                       WHERE fp.produto_id = p.id AND fp.ativo = 1)
               OR (p.custo_unitario IS NOT NULL AND p.custo_unitario > 0))
    """
    params: list = []
    if termo:
        like = f"%{termo}%"
        sql += " AND (p.nome LIKE ? OR p.sku LIKE ? OR p.marca LIKE ?)"
        params += [like, like, like]
    sql += " ORDER BY p.nome, p.sku LIMIT ?"
    params.append(limit)

    with system_conn() as conn:
        rows = [dict(r) for r in conn.execute(sql, params).fetchall()]

    itens = []
    for r in rows:
        calc = calcular_preco(r["id"], margem=m, markup=mk, tabela_id=tabela_id)
        itens.append({
            "produto_id": r["id"],
            "sku": r["sku"],
            "produto_nome": r["produto_nome"],
            "marca": r["marca"],
            "preco_atual": r["preco_atual"] or 0,
            "custo_base": calc.get("custo_base"),
            "custo_liquido": calc.get("custo_liquido"),
            "preco_minimo": calc.get("preco_minimo"),
            "preco_sugerido": calc.get("preco_sugerido"),
            "margem_efetiva_pct": calc.get("margem_efetiva_pct"),
            "observacao": calc.get("observacao"),
        })
    return {"tabela_id": tabela_id, "margem": m, "markup": mk, "total": len(itens), "itens": itens}


def aplicar_reajuste(
    tabela_id: int,
    margem: float | None = None,
    markup: float | None = None,
    usuario_id: int | None = None,
    origem: str = "motor-precificacao",
) -> dict:
    """Aprova e grava o reajuste: atualiza tabela_preco_itens e registra o histórico."""
    prev = previa_reajuste(tabela_id, margem=margem, markup=markup)
    aplicados = 0
    sem_custo = 0
    with system_conn() as conn:
        for it in prev["itens"]:
            if it["preco_sugerido"] is None:
                sem_custo += 1
                continue
            row = conn.execute(
                "SELECT preco FROM tabela_preco_itens WHERE tabela_id=? AND produto_id=?",
                (tabela_id, it["produto_id"]),
            ).fetchone()
            preco_ant = float(row["preco"]) if row else 0.0
            conn.execute(
                "INSERT INTO tabela_preco_itens (tabela_id, produto_id, preco, margem)"
                " VALUES (?,?,?,?)"
                " ON CONFLICT(tabela_id, produto_id) DO UPDATE SET"
                " preco=excluded.preco, margem=excluded.margem",
                (tabela_id, it["produto_id"], it["preco_sugerido"], it["margem_efetiva_pct"]),
            )
            conn.execute(
                "INSERT INTO preco_historico"
                " (tabela_id, produto_id, preco_anterior, preco_novo, margem_pct, markup_pct,"
                "  tipo, origem, usuario_id)"
                " VALUES (?,?,?,?,?,?,'reajuste',?,?)",
                (
                    tabela_id,
                    it["produto_id"],
                    round(preco_ant, 2),
                    it["preco_sugerido"],
                    it["margem_efetiva_pct"],
                    prev["markup"],
                    origem,
                    usuario_id,
                ),
            )
            aplicados += 1
    return {"tabela_id": tabela_id, "aplicados": aplicados, "sem_custo": sem_custo, "total": len(prev["itens"])}
