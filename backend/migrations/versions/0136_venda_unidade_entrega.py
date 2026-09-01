"""Migração 0136 — unidade de venda e retirada/entrega da venda (VEN-001/VEN-005)."""
from __future__ import annotations

VERSION = 136
RISCO = "baixa"  # Expand: colunas novas
NAME = "venda_unidade_entrega"

MUDANCA = {
    "o_que": [
        "orcamento_itens + unidade_vendida e fator_venda (venda por UN/CX/RL com conversão)",
        "orcamentos + tipo_entrega (balcao/entrega), status_entrega (pendente/enviada/entregue), "
        "endereco_entrega, data_entrega",
    ],
    "porque": [
        "Venda fracionada não cria saldo decimal inválido; total e documento fiscal batem (VEN-001)",
        "Separar retirada e entrega na venda (VEN-005)",
    ],
}


def guard(conn) -> bool:
    row = conn.execute(
        "SELECT 1 FROM information_schema.columns "
        "WHERE table_name='orcamento_itens' AND column_name='unidade_vendida'"
    ).fetchone()
    return bool(row)


def forward(conn) -> None:
    conn.execute("ALTER TABLE orcamento_itens ADD COLUMN IF NOT EXISTS unidade_vendida VARCHAR(10) NOT NULL DEFAULT 'UN'")
    conn.execute("ALTER TABLE orcamento_itens ADD COLUMN IF NOT EXISTS fator_venda NUMERIC(14,4) NOT NULL DEFAULT 1")
    conn.execute("ALTER TABLE orcamentos ADD COLUMN IF NOT EXISTS tipo_entrega VARCHAR(10) NOT NULL DEFAULT 'balcao'")
    conn.execute("ALTER TABLE orcamentos ADD COLUMN IF NOT EXISTS status_entrega VARCHAR(12) NOT NULL DEFAULT 'pendente'")
    conn.execute("ALTER TABLE orcamentos ADD COLUMN IF NOT EXISTS endereco_entrega TEXT")
    conn.execute("ALTER TABLE orcamentos ADD COLUMN IF NOT EXISTS data_entrega DATE")
    conn.commit()


def backward(conn) -> None:
    for col in ("unidade_vendida", "fator_venda"):
        conn.execute(f"ALTER TABLE orcamento_itens DROP COLUMN IF EXISTS {col}")
    for col in ("tipo_entrega", "status_entrega", "endereco_entrega", "data_entrega"):
        conn.execute(f"ALTER TABLE orcamentos DROP COLUMN IF EXISTS {col}")