"""Migração 0124 — máquina de estados da solicitação: amplia CHECK de status (COM-007)."""
from __future__ import annotations

VERSION = 124
RISCO = "baixa"  # Expand: amplia CHECK
NAME = "solicitacao_status_check"

MUDANCA = {
    "o_que": [
        "Amplia o CHECK de solicitacao_compra.status para a máquina rascunho→enviada→aprovada→cotando→convertida→cancelada",
    ],
    "porque": [
        "Transições controladas (COM-007); sem select livre de status",
    ],
}


def guard(conn) -> bool:
    row = conn.execute(
        "SELECT pg_get_constraintdef(oid) FROM pg_constraint WHERE conname='solicitacao_compra_status_check'"
    ).fetchone()
    return bool(row and "convertida" in (row["pg_get_constraintdef"] or ""))


def forward(conn) -> None:
    conn.execute("ALTER TABLE solicitacao_compra DROP CONSTRAINT IF EXISTS solicitacao_compra_status_check")
    conn.execute(
        "ALTER TABLE solicitacao_compra ADD CONSTRAINT solicitacao_compra_status_check"
        " CHECK (status IN ('rascunho','enviada','aprovada','cotando','convertida','cancelada'))"
    )
    conn.commit()


def backward(conn) -> None:
    conn.execute("ALTER TABLE solicitacao_compra DROP CONSTRAINT IF EXISTS solicitacao_compra_status_check")