"""Migração 0111 — disponibilidade de estoque: bloqueado, separação e trânsito (EST-001)."""
from __future__ import annotations

VERSION = 111
RISCO = "baixa"  # Expand: colunas com default 0, fórmula de disponível unificada
NAME = "estoque_disponibilidade"

MUDANCA = {
    "o_que": [
        "Adiciona estoque_saldo.bloqueado, .separacao e .transito (default 0)",
        "Disponível passa a ser físico − reservado − bloqueado − separação em todas as leituras",
    ],
    "porque": [
        "Fórmula única de disponibilidade no service de estoque, exposta nas APIs (EST-001)",
        "Reserva/bloqueio/separação reduzem disponível, nunca o físico; trânsito é saldo próprio",
    ],
}


def guard(conn) -> bool:
    row = conn.execute(
        "SELECT 1 FROM information_schema.columns "
        "WHERE table_name='estoque_saldo' AND column_name='bloqueado'"
    ).fetchone()
    return bool(row)


def forward(conn) -> None:
    for col in ("bloqueado", "separacao", "transito"):
        conn.execute(
            f"ALTER TABLE estoque_saldo ADD COLUMN IF NOT EXISTS {col} "
            "NUMERIC(14,3) NOT NULL DEFAULT 0"
        )
    conn.commit()


def backward(conn) -> None:
    for col in ("bloqueado", "separacao", "transito"):
        conn.execute(f"ALTER TABLE estoque_saldo DROP COLUMN IF EXISTS {col}")