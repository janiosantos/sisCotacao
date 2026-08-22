"""Snapshot fiscal e auditoria ('por que esta tributação?' — §14/§22).

`persistir()` é tolerante a falhas por design: emissão NUNCA deve quebrar
porque o snapshot falhou. `explicar()` devolve os snapshots do documento.
"""
from __future__ import annotations

import json

from catalog_server.db import system_conn
from catalog_server.fiscal.resultado import FiscalResult


def persistir(
    *,
    documento_tipo: str,
    documento_id: int,
    document_number: str = "",
    variante_id: int | None = None,
    produto_nome: str = "",
    operation_date: str = "",
    result: FiscalResult | None = None,
    bases: dict | None = None,
    rates: dict | None = None,
    values: dict | None = None,
    inputs: dict | None = None,
) -> int | None:
    """Grava um snapshot; retorna id ou None em caso de falha silenciosa."""
    try:
        d = result.para_dict() if result else {}
        with system_conn() as conn:
            cur = conn.execute(
                """
                INSERT INTO fiscal_snapshot (
                    documento_tipo, documento_id, document_number, variante_id,
                    produto_nome, rule_id, rule_version, operation_date,
                    cfop, cst, csosn, bases, rates, values,
                    legal_reference, source_url, calculation_inputs, status
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    documento_tipo,
                    documento_id,
                    document_number,
                    variante_id,
                    produto_nome,
                    d.get("rule_id"),
                    _int(d.get("rule_version")),
                    operation_date,
                    d.get("cfop") or "",
                    d.get("cst") or "",
                    d.get("csosn") or "",
                    json.dumps(bases or {}, ensure_ascii=False),
                    json.dumps(rates or {}, ensure_ascii=False),
                    json.dumps(values or {}, ensure_ascii=False),
                    d.get("legal_reference") or "",
                    d.get("source_url"),
                    json.dumps(inputs or {}, ensure_ascii=False),
                    d.get("status", "CALCULATED"),
                ),
            )
            conn.commit()
            return int(cur.lastrowid)
    except Exception:
        return None


def explicar(documento_tipo: str, documento_id: int) -> list[dict]:
    """Snapshots do documento — resposta pronta para 'por que esta tributação?'."""
    with system_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM fiscal_snapshot"
            " WHERE documento_tipo=? AND documento_id=?"
            " ORDER BY id",
            (documento_tipo, documento_id),
        ).fetchall()
        return [dict(r) for r in rows]


def _int(v):
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


def montar_contextos_orcamento(orcamento_id: int):
    """Gera (ctx_dados, FiscalResult) por item do orçamento.

    Com FISCAL_ENGINE_V2 ligada usa o resolvedor versionado; sem a flag,
    devolve FISCAL_REVIEW_REQUIRED — nunca inventa tributação (§26).
    """
    from datetime import date as _date

    from catalog_server import flags
    from catalog_server.fiscal.estados import EstadoFiscal
    from catalog_server.fiscal.resolvedor import resolver_v2

    hoje = _date.today().isoformat()
    with system_conn() as conn:
        uf_row = conn.execute(
            "SELECT uf FROM emitente WHERE ativo=1 LIMIT 1"
        ).fetchone()
        uf_origin = ((uf_row["uf"] if uf_row else "") or "").strip().upper()
        itens = conn.execute(
            "SELECT * FROM orcamento_itens WHERE orcamento_id=? ORDER BY id",
            (orcamento_id,),
        ).fetchall()
        perfis = {
            p["variante_id"]: dict(p)
            for p in conn.execute("SELECT * FROM product_fiscal_profile").fetchall()
        }

    for it in itens:
        vid = it["produto_id"]
        perfil = perfis.get(vid) or {}
        ctx_dados = {
            "tax_regime": "simples_nacional",
            "uf_origin": uf_origin,
            "operation_date": hoje,
            "operation_type": "venda",
            "product_id": vid,
            "ncm": perfil.get("ncm", ""),
            "cest": perfil.get("cest", ""),
            "merchandise_origin": str(perfil.get("origem") or ""),
            "quantity": it["quantidade"],
            "unit_price": it["preco_unitario"],
        }
        if flags.ativa("FISCAL_ENGINE_V2"):
            resultado = resolver_v2(ctx_dados)
        else:
            resultado = FiscalResult(
                status=EstadoFiscal.FISCAL_REVIEW_REQUIRED,
                errors=[
                    "Motor v2 desligado e regras normativas não validadas — "
                    "revenda exige revisão fiscal (§26)"
                ],
                cfop=None,
            )
        yield ctx_dados, resultado
