"""Migração 0073 — tipos de movimento de estoque: reserva/liberação (ADR 0003).

Alarga o CHECK de `estoque_movimento.tipo` para incluir reserva/liberacao,
usados como fatos próprios (não alteram saldo, apenas reserva).
"""
from __future__ import annotations

VERSION = 73
RISCO = "rotina"
NAME = "estoque_tipos_reserva"

MUDANCA = {
    "o_que": ["Alarga CHECK de estoque_movimento.tipo para incluir reserva e liberacao"],
    "porque": ["Reservas/liberações como fatos auditáveis próprios (ADR 0003)"],
}


def guard(conn) -> bool:
    row = conn.execute(
        "SELECT pg_get_constraintdef(oid) FROM pg_constraint"
        " WHERE conname='estoque_movimento_tipo_check'"
    ).fetchone()
    return row is not None and "reserva" in (row[0] or "")


def forward(conn) -> None:
    ac = conn.autocommit
    conn.autocommit = True
    try:
        conn.execute(
            "ALTER TABLE estoque_movimento DROP CONSTRAINT IF EXISTS"
            " estoque_movimento_tipo_check"
        )
        conn.execute(
            "ALTER TABLE estoque_movimento ADD CONSTRAINT"
            " estoque_movimento_tipo_check CHECK (tipo IN"
            " ('entrada','saida','ajuste','transferencia','inventario',"
            "'reserva','liberacao'))"
        )
    finally:
        conn.autocommit = ac


def backward(conn) -> None:
    ac = conn.autocommit
    conn.autocommit = True
    try:
        conn.execute(
            "ALTER TABLE estoque_movimento DROP CONSTRAINT IF EXISTS"
            " estoque_movimento_tipo_check"
        )
    finally:
        conn.autocommit = ac
