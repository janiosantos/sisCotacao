"""Migração 0130 — conferência por código/unidade no recebimento (REC-002)."""
from __future__ import annotations

VERSION = 130
RISCO = "baixa"  # Expand: colunas novas
NAME = "recebimento_conferencia"

MUDANCA = {
    "o_que": [
        "recebimento_item + codigo_conferido (código escaneado) e unidade_conferida (UN/CX/RL…)",
    ],
    "porque": [
        "Caixa/rolo não gera quantidade errada; produto desconhecido vai para exceção (REC-002)",
    ],
}


def guard(conn) -> bool:
    row = conn.execute(
        "SELECT 1 FROM information_schema.columns "
        "WHERE table_name='recebimento_item' AND column_name='codigo_conferido'"
    ).fetchone()
    return bool(row)


def forward(conn) -> None:
    conn.execute("ALTER TABLE recebimento_item ADD COLUMN IF NOT EXISTS codigo_conferido VARCHAR(40)")
    conn.execute("ALTER TABLE recebimento_item ADD COLUMN IF NOT EXISTS unidade_conferida VARCHAR(10)")
    conn.commit()


def backward(conn) -> None:
    for col in ("codigo_conferido", "unidade_conferida"):
        conn.execute(f"ALTER TABLE recebimento_item DROP COLUMN IF EXISTS {col}")