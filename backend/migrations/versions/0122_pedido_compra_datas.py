"""Migração 0122 — datas de prazo/envio/recebimento no pedido de compra (COM-005)."""
from __future__ import annotations

VERSION = 122
RISCO = "baixa"  # Expand: colunas novas
NAME = "pedido_compra_datas"

MUDANCA = {
    "o_que": [
        "pedidos_compra + data_prometida, data_enviada, data_recebida, data_aceita "
        "(para medir lead time real, atraso e fill rate — COM-005)",
    ],
    "porque": [
        "Desempenho real do fornecedor usa datas prometida/enviada/recebida/aceita",
    ],
}


def guard(conn) -> bool:
    row = conn.execute(
        "SELECT 1 FROM information_schema.columns "
        "WHERE table_name='pedidos_compra' AND column_name='data_prometida'"
    ).fetchone()
    return bool(row)


def forward(conn) -> None:
    for col in ("data_prometida", "data_enviada", "data_recebida", "data_aceita"):
        conn.execute(f"ALTER TABLE pedidos_compra ADD COLUMN IF NOT EXISTS {col} TIMESTAMPTZ")
    conn.commit()


def backward(conn) -> None:
    for col in ("data_prometida", "data_enviada", "data_recebida", "data_aceita"):
        conn.execute(f"ALTER TABLE pedidos_compra DROP COLUMN IF EXISTS {col}")