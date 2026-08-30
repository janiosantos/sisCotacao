"""Migração 0097 — fixa o ambiente da cobrança na conta a receber.

Expand-only: a emissão passa a registrar se foi feita em sandbox ou produção,
permitindo consultar e processar webhooks no mesmo ambiente.
"""
from __future__ import annotations

VERSION = 97
RISCO = "moderada"
NAME = "cobranca_ambiente"

MUDANCA = {
    "o_que": ["contas_receber: ambiente_cobranca (sandbox/producao)"],
    "porque": [
        "Consultas e webhooks precisam usar o mesmo ambiente em que a cobrança foi emitida",
        "Evita consultar cobranças de produção contra endpoints sandbox",
    ],
}


def guard(conn) -> bool:
    row = conn.execute(
        "SELECT 1 FROM information_schema.columns "
        "WHERE table_schema='public' AND table_name='contas_receber' "
        "AND column_name='ambiente_cobranca'"
    ).fetchone()
    return row is not None


def forward(conn) -> None:
    conn.execute(
        "ALTER TABLE contas_receber ADD COLUMN IF NOT EXISTS "
        "ambiente_cobranca TEXT NOT NULL DEFAULT 'sandbox'"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_contas_receber_payment_id "
        "ON contas_receber (payment_id) WHERE payment_id IS NOT NULL"
    )


def backward(conn) -> None:
    conn.execute(
        "DROP INDEX IF EXISTS idx_contas_receber_payment_id"
    )
    conn.execute(
        "ALTER TABLE contas_receber DROP COLUMN IF EXISTS ambiente_cobranca"
    )
