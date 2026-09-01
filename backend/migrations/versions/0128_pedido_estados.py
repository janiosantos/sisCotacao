"""Migração 0128 — máquina de estados do pedido de compra (COM-011)."""
from __future__ import annotations

VERSION = 128
RISCO = "baixa"  # Expand: CHECK novo (status existentes são válidos)
NAME = "pedido_estados"

MUDANCA = {
    "o_que": [
        "Amplia pedidos_compra com data_pedido e CHECK de status da máquina "
        "rascunho→aprovado→enviado→confirmado→parcialmente_recebido→recebido, cancelado",
    ],
    "porque": [
        "Pedido enviado é imutável; saldo cancelado não pode ser recebido (COM-011)",
    ],
}


def guard(conn) -> bool:
    row = conn.execute(
        "SELECT 1 FROM information_schema.columns "
        "WHERE table_name='pedidos_compra' AND column_name='data_pedido'"
    ).fetchone()
    return bool(row)


def forward(conn) -> None:
    conn.execute("ALTER TABLE pedidos_compra ADD COLUMN IF NOT EXISTS data_pedido TIMESTAMPTZ DEFAULT NOW()")
    conn.execute("ALTER TABLE pedidos_compra DROP CONSTRAINT IF EXISTS chk_pedido_status")
    conn.execute(
        "ALTER TABLE pedidos_compra ADD CONSTRAINT chk_pedido_status"
        " CHECK (status IN ('rascunho','aprovado','enviado','confirmado','parcialmente_recebido','recebido','cancelado'))"
    )
    conn.commit()


def backward(conn) -> None:
    conn.execute("ALTER TABLE pedidos_compra DROP CONSTRAINT IF EXISTS chk_pedido_status")
    conn.execute("ALTER TABLE pedidos_compra DROP COLUMN IF EXISTS data_pedido")