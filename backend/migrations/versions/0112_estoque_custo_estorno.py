"""Migração 0112 — custo unitário no movimento, custo médio por depósito e estorno (EST-002/003)."""
from __future__ import annotations

VERSION = 112
RISCO = "moderada"  # Expand: colunas novas com default; comportamento novo atrás do serviço
NAME = "estoque_custo_estorno"

MUDANCA = {
    "o_que": [
        "estoque_movimento + custo_unitario, custo_medio_anterior e estorno_de (cadeia de estorno)",
        "estoque_saldo + custo_medio (média ponderada por depósito, DECISAO-002)",
        "Índice em estoque_movimento(estorno_de)",
    ],
    "porque": [
        "Margem e CMV reproduzem o custo do momento; não usar custo atual para histórico (EST-003)",
        "Correção é estorno + novo fato, nunca edição de movimento (EST-002)",
    ],
}


def guard(conn) -> bool:
    row = conn.execute(
        "SELECT 1 FROM information_schema.columns "
        "WHERE table_name='estoque_movimento' AND column_name='custo_unitario'"
    ).fetchone()
    return bool(row)


def forward(conn) -> None:
    conn.execute(
        "ALTER TABLE estoque_movimento ADD COLUMN IF NOT EXISTS custo_unitario NUMERIC(14,4)"
    )
    conn.execute(
        "ALTER TABLE estoque_movimento ADD COLUMN IF NOT EXISTS custo_medio_anterior NUMERIC(14,4)"
    )
    conn.execute(
        "ALTER TABLE estoque_movimento ADD COLUMN IF NOT EXISTS estorno_de BIGINT"
    )
    conn.execute(
        "ALTER TABLE estoque_saldo ADD COLUMN IF NOT EXISTS custo_medio NUMERIC(14,4) NOT NULL DEFAULT 0"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_estoque_movimento_estorno "
        "ON estoque_movimento (estorno_de)"
    )
    conn.commit()


def backward(conn) -> None:
    for col in ("custo_unitario", "custo_medio_anterior", "estorno_de"):
        conn.execute(f"ALTER TABLE estoque_movimento DROP COLUMN IF EXISTS {col}")
    conn.execute("ALTER TABLE estoque_saldo DROP COLUMN IF EXISTS custo_medio")