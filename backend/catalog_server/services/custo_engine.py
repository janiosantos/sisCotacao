"""Motor de Custo Líquido.

Consome o resultado do Motor Fiscal (`fiscal_engine.calculate`) e a fonte de
custo (`fornecedor_preco` → `fornecedor_preferencial` → `variantes.custo_unitario`)
para calcular o custo líquido de aquisição de uma variante.

Fórmula (documentada):
    custo_liquido = custo_base − créditos_recuperáveis + ICMS-ST_não_recuperado

Onde:
- créditos_recuperáveis = custo_base × fiscal.creditos.total_pct / 100
  (ICMS, PIS, COFINS e IPI recuperáveis conforme o regime do emitente — o Motor
  Fiscal decide, este módulo apenas consome).
- ICMS-ST_não_recuperado = custo_base × fiscal.icms_st.aliquota / 100 quando a
  ST incide na entrada (ST não gera crédito e integra o custo).

Este módulo NÃO calcula margem, markup ou preço de venda (responsabilidade do
Módulo de Precificação) e NÃO recalcula tributos.
"""
from __future__ import annotations

from catalog_server.db import system_conn
from catalog_server.services import fiscal_engine


def preco_compra(produto_id: int, fornecedor_id: int | None = None) -> float | None:
    """Melhor preço de compra da variante (R$)."""
    with system_conn() as conn:
        if fornecedor_id:
            row = conn.execute(
                "SELECT preco FROM fornecedor_preco"
                " WHERE produto_id=? AND fornecedor_id=? AND ativo=1",
                (produto_id, fornecedor_id),
            ).fetchone()
        else:
            row = conn.execute(
                "SELECT preco FROM fornecedor_preco"
                " WHERE produto_id=? AND ativo=1 ORDER BY preco ASC LIMIT 1",
                (produto_id,),
            ).fetchone()
        if row:
            return float(row["preco"])
        row = conn.execute(
            "SELECT custo_unitario FROM produtos_cadastro WHERE id=?", (produto_id,)
        ).fetchone()
        if row and row["custo_unitario"]:
            return float(row["custo_unitario"])
    return None


def calcular_custo(
    produto_id: int,
    fornecedor_id: int | None = None,
) -> dict:
    base = preco_compra(produto_id, fornecedor_id)
    if base is None:
        return {
            "produto_id": produto_id,
            "fornecedor_id": fornecedor_id,
            "regime": None,
            "custo_base": None,
            "creditos_pct": 0,
            "creditos_valor": 0,
            "icms_st_aplica": False,
            "icms_st_nao_recuperavel": 0,
            "custo_liquido": None,
            "fiscal": None,
        }

    fiscal = fiscal_engine.calculate(produto_id, "compra")
    credito_pct = float((fiscal or {}).get("creditos", {}).get("total_pct") or 0)
    credito_valor = round(base * credito_pct / 100, 2)

    st = (fiscal or {}).get("icms_st", {}) or {}
    st_aplica = bool(st.get("aplica"))
    st_aliquota = float(st.get("aliquota") or 0)
    st_nao_recuperavel = round(base * st_aliquota / 100, 2) if st_aplica else 0.0

    custo_liquido = round(base - credito_valor + st_nao_recuperavel, 2)
    return {
        "produto_id": produto_id,
        "fornecedor_id": fornecedor_id,
        "regime": (fiscal or {}).get("regime"),
        "custo_base": round(base, 2),
        "creditos_pct": credito_pct,
        "creditos_valor": credito_valor,
        "icms_st_aplica": st_aplica,
        "icms_st_aliquota": st_aliquota,
        "icms_st_nao_recuperavel": st_nao_recuperavel,
        "custo_liquido": custo_liquido,
        "fiscal": fiscal,
    }
