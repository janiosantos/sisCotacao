"""Motor Fiscal — calcula a tributação e créditos de um produto/variante.

Módulo Fiscal: responsável apenas por classificação fiscal, regras, alíquotas,
carga tributária e créditos. NÃO conhece margem, comissão, markup ou canal de
venda. O módulo de Precificação consome `fiscal_engine.calculate()` e usa o
resultado (créditos, ICMS-ST, DIFAL) para o cálculo de custo líquido.

Operação: `compra` (entrada) ou `venda` (saída). Para venda, `uf_dest` é usado
no DIFAL. O regime tributário do emitente (Simples Nacional / Lucro Presumido /
Lucro Real) muda as alíquotas e os créditos recuperáveis.
"""
from __future__ import annotations

from datetime import date

from catalog_server.db import system_conn
from catalog_server.services import fiscal_regras

# CSOSN que indicam ICMS-ST no Simples Nacional.
CSOSN_ST = {"106", "107", "201", "202", "203", "205", "206", "207", "208", "209"}
# CST ICMS que indicam ICMS-ST (tributação normal / reduzida + ST).
CST_ICMS_ST = {"10", "70"}


def _hoje() -> str:
    return date.today().isoformat()


def _vigente(inicio: str | None, fim: str | None) -> bool | None:
    """None = sem vigência definida; True/False = dentro/fora."""
    if not inicio and not fim:
        return None
    hoje = _hoje()
    if inicio and fim:
        return inicio <= hoje <= fim
    if inicio:
        return hoje >= inicio
    return hoje <= fim


def _pct(valor, default: float) -> float:
    try:
        v = float(valor or 0)
    except (TypeError, ValueError):
        return round(default, 4)
    return round(v, 4) if v > 0 else round(default, 4)


def calculate(
    variante_id: int,
    operacao: str = "compra",
    uf_dest: str | None = None,
    tipo_cliente: str | None = None,
    contribuinte: str | None = None,
) -> dict | None:
    operacao = operacao if operacao in ("compra", "venda") else "compra"
    uf_dest = (uf_dest or "").strip().upper() or None

    with system_conn() as conn:
        row = conn.execute(
            "SELECT * FROM fiscal_config WHERE variante_id=?", (variante_id,)
        ).fetchone()
        if row is None:
            return None
        cfg = dict(row)

        emit = conn.execute(
            "SELECT * FROM emitente WHERE ativo=1 LIMIT 1"
        ).fetchone()
        emit = dict(emit) if emit else {}

        beneficio = None
        if cfg.get("beneficio_id"):
            b = conn.execute(
                "SELECT * FROM beneficios_fiscais WHERE id=? AND ativo=1",
                (cfg["beneficio_id"],),
            ).fetchone()
            if b:
                b = dict(b)
                beneficio = {
                    "codigo": b.get("codigo"),
                    "descricao": b.get("descricao"),
                    "tipo": b.get("tipo"),
                    "valor": float(b.get("valor_default") or 0),
                    "vigente": _vigente(b.get("vigencia_inicio"), b.get("vigencia_fim")),
                }

        ncm = (cfg.get("ncm") or "").strip()
        ibpt = None
        if ncm:
            cand = conn.execute(
                "SELECT * FROM ibpt WHERE ncm LIKE ? ORDER BY length(ncm) ASC LIMIT 1",
                (ncm[:4] + "%",),
            ).fetchone()
            if cand:
                cand = dict(cand)
                ibpt = {
                    "ncm": cand.get("ncm"),
                    "federal": float(cand.get("aliquota_federal") or 0),
                    "estadual": float(cand.get("aliquota_estadual") or 0),
                    "municipal": float(cand.get("aliquota_municipal") or 0),
                    "vigente": _vigente(cand.get("vigencia_inicio"), cand.get("vigencia_fim")),
                }

    regime = (emit.get("regime_tributario") or "simples_nacional").strip()
    uf_origem = (emit.get("uf") or "").strip().upper()

    icms = _pct(cfg.get("aliquota_icms"), _pct(emit.get("aliquota_icms"), 18.0))
    pis = _pct(cfg.get("aliquota_pis"), _pct(emit.get("aliquota_pis"), 0.0))
    cofins = _pct(cfg.get("aliquota_cofins"), _pct(emit.get("aliquota_cofins"), 0.0))
    ipi = _pct(cfg.get("aliquota_ipi"), _pct(emit.get("aliquota_ipi"), 0.0))
    icms_st = _pct(cfg.get("aliquota_icms_st"), 0.0)
    mva = _pct(cfg.get("mva"), 0.0)
    base_reducao = _pct(cfg.get("base_reducao"), 0.0)
    interestadual = _pct(cfg.get("aliquota_interestadual"), 0.0)
    fecp = _pct(cfg.get("aliquota_fecp"), 0.0)
    credito_cfg = _pct(cfg.get("credito_icms"), 0.0)

    cst_icms = (cfg.get("cst_icms") or "").strip()
    csosn = (cfg.get("csosn") or "").strip()

    # ── ICMS-ST ─────────────────────────────────────────────
    aplica_st = (
        icms_st > 0
        or cst_icms in CST_ICMS_ST
        or (regime == "simples_nacional" and csosn in CSOSN_ST)
    )

    # ── DIFAL (venda para outra UF) ─────────────────────────
    difal_aplica = (
        operacao == "venda"
        and uf_dest is not None
        and bool(uf_origem)
        and uf_dest != uf_origem
    )

    # ── Créditos na compra (custo líquido) ──────────────────
    if regime == "simples_nacional":
        cred_icms = 0.0
        cred_pis = 0.0
        cred_cofins = 0.0
        cred_ipi = 0.0
    elif regime == "lucro_presumido":
        cred_icms = credito_cfg or icms
        cred_pis = 0.0
        cred_cofins = 0.0
        cred_ipi = ipi
    else:  # lucro_real
        cred_icms = credito_cfg or icms
        cred_pis = pis
        cred_cofins = cofins
        cred_ipi = ipi

    credito_pct = round(cred_icms + cred_pis + cred_cofins + cred_ipi, 4)

    # ── Carga tributária na venda ───────────────────────────
    if regime == "simples_nacional":
        carga_icms = 0.0
        carga_pis = 0.0
        carga_cofins = 0.0
        carga_ipi = ipi
    else:
        carga_icms = icms
        carga_pis = pis
        carga_cofins = cofins
        carga_ipi = ipi
    carga_venda_pct = round(carga_icms + carga_pis + carga_cofins + carga_ipi, 4)

    resultado = {
        "variante_id": variante_id,
        "operacao": operacao,
        "regime": regime,
        "uf_origem": uf_origem,
        "uf_dest": uf_dest,
        # Classificação
        "ncm": ncm,
        "cest": (cfg.get("cest") or "").strip(),
        "cfop": (cfg.get("cfop") or "").strip(),
        "origem": int(cfg.get("origem") or 0),
        "cst_icms": cst_icms,
        "cst_pis": (cfg.get("cst_pis") or "").strip(),
        "cst_cofins": (cfg.get("cst_cofins") or "").strip(),
        "csosn": csosn,
        # Alíquotas efetivas
        "aliquota_icms": icms,
        "aliquota_pis": pis,
        "aliquota_cofins": cofins,
        "aliquota_ipi": ipi,
        # ICMS-ST
        "icms_st": {
            "aplica": aplica_st,
            "aliquota": icms_st,
            "mva": mva,
            "base_reducao": base_reducao,
        },
        # DIFAL
        "difal": {
            "aplica": difal_aplica,
            "uf_origem": uf_origem,
            "uf_dest": uf_dest,
            "aliquota_interestadual": interestadual,
            "aliquota_fecp": fecp,
        },
        # Benefício fiscal
        "beneficio": beneficio,
        # Vigência
        "vigencia": {
            "config": _vigente(cfg.get("vigencia_inicio"), cfg.get("vigencia_fim")),
            "inicio": cfg.get("vigencia_inicio"),
            "fim": cfg.get("vigencia_fim"),
        },
        # Créditos recuperáveis (compra)
        "creditos": {
            "icms": round(cred_icms, 4),
            "pis": round(cred_pis, 4),
            "cofins": round(cred_cofins, 4),
            "ipi": round(cred_ipi, 4),
            "total_pct": credito_pct,
        },
        # Carga tributária (venda)
        "carga": {
            "icms": carga_icms,
            "pis": carga_pis,
            "cofins": carga_cofins,
            "ipi": carga_ipi,
            "total_pct": carga_venda_pct,
        },
        # Referência IBPT (carga por NCM)
        "ibpt": ibpt,
        # Transição tributária (IBS/CBS) — parâmetros com vigência
        # (NECESSITA VALIDAÇÃO; cálculo na fase IBS/CBS)
        "transicao": {
            "crt": int(emit.get("crt") or 1),
            "aliquota_ibs": float(emit.get("aliquota_ibs") or 0),
            "aliquota_cbs": float(emit.get("aliquota_cbs") or 0),
            "ibs_vigencia": {
                "inicio": emit.get("ibs_vigencia_inicio"),
                "fim": emit.get("ibs_vigencia_fim"),
            },
            "cbs_vigencia": {
                "inicio": emit.get("cbs_vigencia_inicio"),
                "fim": emit.get("cbs_vigencia_fim"),
            },
        },
    }

    # CFOP contextual: a matriz de regras decide quando há contexto
    # (tipo_cliente/contribuinte informados); senão, usa a config do produto.
    resultado["cfop_origem"] = "config"
    if tipo_cliente or contribuinte:
        regra = fiscal_regras.buscar_regra({
            "regime": regime,
            "uf_origem": uf_origem,
            "uf_destino": uf_dest,
            "tipo_cliente": tipo_cliente,
            "contribuinte": contribuinte,
            "natureza_operacao": operacao,
            "ncm": ncm,
            "cest": (cfg.get("cest") or "").strip(),
            "origem": cfg.get("origem") or "",
        })
        cfop_regra = ((regra or {}).get("cfop") or "").strip()
        if cfop_regra:
            resultado["cfop"] = cfop_regra
            resultado["cfop_origem"] = "regra"
            resultado["cfop_regra"] = {
                "id": regra.get("id"),
                "nome": regra.get("nome"),
                "versao": (regra.get("versao") or {}).get("versao"),
            }
    return resultado
