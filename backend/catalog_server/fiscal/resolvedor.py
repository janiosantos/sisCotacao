"""Resolvedor do motor fiscal v2 — regras PUBLISHED versionadas por vigência.

Semântica (skill fiscal-mg §12-13):
- Seleção usa a DATA DA OPERAÇÃO, não a data atual.
- Prioridade MENOR número = mais específico/precedente.
- Empate de prioridade entre resultados distintos -> FISCAL_RULE_CONFLICT.
- Nenhum match -> RULE_NOT_FOUND. Nunca devolve zero silencioso.
"""
from __future__ import annotations

from datetime import date

from catalog_server.db import system_conn
from catalog_server.fiscal.contexto import FiscalContext
from catalog_server.fiscal.decimais import aliquota
from catalog_server.fiscal.estados import EstadoFiscal
from catalog_server.fiscal.resultado import FiscalResult


def _hoje() -> str:
    return date.today().isoformat()


def _condicao_casa(operador: str, exigido: str, valor_ctx: str) -> bool:
    if operador == "prefixo":
        return valor_ctx.startswith(exigido)
    return exigido == valor_ctx


def _valor_contexto(ctx: FiscalContext, campo: str) -> str:
    bruto = getattr(ctx, campo, None)
    if bruto is ctx.extras:
        bruto = ctx.extras.get(campo)
    return str(bruto or "").strip()


def _candidatos(ctx: FiscalContext, data: str) -> list[dict]:
    with system_conn() as conn:
        rows = conn.execute(
            """
            SELECT r.id AS rule_id, r.code, r.nome, r.prioridade,
                   v.id AS version_id, v.version, v.source_url,
                   v.legal_reference,
                   er.cfop, er.cst_icms, er.csosn, er.cst_pis, er.cst_cofins,
                   er.modalidade_st, er.aliquota_icms, er.mva, er.base_reducao,
                   er.aliquota_icms_st, er.aliquota_pis, er.aliquota_cofins
            FROM fiscal_engine_rule r
            JOIN fiscal_engine_rule_version v ON v.rule_id = r.id
            JOIN fiscal_engine_rule_result er ON er.version_id = v.id
            WHERE r.estado = 'PUBLISHED'
              AND v.valid_from <= ? AND (v.valid_to IS NULL OR v.valid_to >= ?)
            ORDER BY r.prioridade ASC, r.id ASC, v.version DESC
            """,
            (data, data),
        ).fetchall()
        candidatos = [dict(r) for r in rows]
        conds = conn.execute(
            """
            SELECT c.version_id, c.campo, c.operador, c.valor
            FROM fiscal_engine_rule_condition c
            JOIN fiscal_engine_rule_version v ON v.id = c.version_id
            JOIN fiscal_engine_rule r ON r.id = v.rule_id
            WHERE r.estado = 'PUBLISHED'
            """
        ).fetchall()
    por_versao: dict[int, list[dict]] = {}
    for cnd in conds:
        por_versao.setdefault(cnd["version_id"], []).append(dict(cnd))
    for cand in candidatos:
        cand["conditions"] = por_versao.get(cand["version_id"], [])
    return candidatos


def _casa(candidato: dict, ctx: FiscalContext) -> bool:
    for cond in candidato["conditions"]:
        valor_ctx = _valor_contexto(ctx, cond["campo"])
        if not _condicao_casa(cond["operador"], cond["valor"], valor_ctx):
            return False
    return True


def resolver_v2(
    ctx: FiscalContext | dict,
    data_operacao: str | None = None,
) -> FiscalResult:
    """Resolve CFOP/CST/CSOSN e parâmetros a partir das regras publicadas."""
    contexto = (
        FiscalContext.de_dict(ctx) if isinstance(ctx, dict) else ctx
    )
    data = data_operacao or contexto.operation_date or _hoje()

    casadas = [c for c in _candidatos(contexto, data) if _casa(c, contexto)]
    if not casadas:
        return FiscalResult(status=EstadoFiscal.RULE_NOT_FOUND)

    melhor_prioridade = min(c["prioridade"] for c in casadas)
    finalistas = [c for c in casadas if c["prioridade"] == melhor_prioridade]

    resultados_distintos = {
        tuple(sorted((k, str(v)) for k, v in f.items()
                     if k.startswith(("cfop", "cst", "csosn"))))
        for f in finalistas
    }
    base_kwargs = {
        "rule_id": finalistas[0]["rule_id"],
        "rule_version": finalistas[0]["version"],
        "legal_reference": finalistas[0]["legal_reference"] or None,
        "source_url": finalistas[0]["source_url"] or None,
        "matched_conditions": [
            f"{c['campo']}={c['valor']}"
            for c in finalistas[0]["conditions"]
        ],
    }
    if len(resultados_distintos) > 1:
        conflito = FiscalResult(
            status=EstadoFiscal.FISCAL_RULE_CONFLICT, **base_kwargs
        )
        conflito.errors.append(
            "Regras de mesma prioridade com resultados distintos: "
            + ", ".join(f"#{f['rule_id']}" for f in finalistas)
        )
        return conflito

    f = finalistas[0]
    return FiscalResult(
        status=EstadoFiscal.CALCULATED,
        cfop=f["cfop"] or None,
        cst=f["cst_icms"] or None,
        csosn=f["csosn"] or None,
        icms_rate=aliquota(f["aliquota_icms"]),
        icms_st_rate=aliquota(f["aliquota_icms_st"]),
        rule_id=f["rule_id"],
        rule_version=f["version"],
        legal_reference=f["legal_reference"] or None,
        source_url=f["source_url"] or None,
        matched_conditions=[
            f"{c['campo']}{'~' if c['operador'] == 'prefixo' else '='}{c['valor']}"
            for c in f["conditions"]
        ],
    )
