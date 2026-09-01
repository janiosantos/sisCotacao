"""Migração 0120 — política 'sob_encomenda' no estoque_parametro (COM-004)."""
from __future__ import annotations

VERSION = 120
RISCO = "baixa"  # Expand: amplia CHECK (compatível: valores existentes continuam válidos)
NAME = "politica_sob_encomenda"

MUDANCA = {
    "o_que": [
        "Amplia o CHECK de estoque_parametro.politica para incluir 'sob_encomenda'",
    ],
    "porque": [
        "Compra sob encomenda não vira estoque automático no motor de reposição (COM-004)",
    ],
}


def guard(conn) -> bool:
    row = conn.execute(
        "SELECT pg_get_constraintdef(oid) FROM pg_constraint WHERE conname='chk_estoque_parametro_politica'"
    ).fetchone()
    return bool(row and "sob_encomenda" in (row["pg_get_constraintdef"] or ""))


def forward(conn) -> None:
    conn.execute("ALTER TABLE estoque_parametro DROP CONSTRAINT IF EXISTS chk_estoque_parametro_politica")
    conn.execute(
        "ALTER TABLE estoque_parametro ADD CONSTRAINT chk_estoque_parametro_politica"
        " CHECK (politica IN ('manual','calculada','sob_encomenda'))"
    )
    conn.commit()


def backward(conn) -> None:
    conn.execute("ALTER TABLE estoque_parametro DROP CONSTRAINT IF EXISTS chk_estoque_parametro_politica")
    conn.execute(
        "ALTER TABLE estoque_parametro ADD CONSTRAINT chk_estoque_parametro_politica"
        " CHECK (politica IN ('manual','calculada'))"
    )