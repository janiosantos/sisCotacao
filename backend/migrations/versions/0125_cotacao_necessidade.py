"""Migração 0125 — cotação a partir de necessidade: vínculo solicitação→cotação e versão (COM-008)."""
from __future__ import annotations

VERSION = 125
RISCO = "baixa"  # Expand: colunas novas
NAME = "cotacao_necessidade"

MUDANCA = {
    "o_que": [
        "cotacoes + solicitacao_id, versao",
        "cotacao_itens + solicitacao_item_id (origem rastreável)",
    ],
    "porque": [
        "Comando idempotente consolida itens compatíveis; origem é rastreável; alterações têm versão (COM-008)",
    ],
}


def guard(conn) -> bool:
    row = conn.execute(
        "SELECT 1 FROM information_schema.columns "
        "WHERE table_name='cotacoes' AND column_name='solicitacao_id'"
    ).fetchone()
    return bool(row)


def forward(conn) -> None:
    conn.execute("ALTER TABLE cotacoes ADD COLUMN IF NOT EXISTS solicitacao_id BIGINT")
    conn.execute("ALTER TABLE cotacoes ADD COLUMN IF NOT EXISTS versao INTEGER NOT NULL DEFAULT 1")
    conn.execute("ALTER TABLE cotacao_itens ADD COLUMN IF NOT EXISTS solicitacao_item_id BIGINT")
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_cotacao_solicitacao ON cotacoes (solicitacao_id)"
    )
    conn.commit()


def backward(conn) -> None:
    conn.execute("ALTER TABLE cotacoes DROP COLUMN IF EXISTS solicitacao_id")
    conn.execute("ALTER TABLE cotacoes DROP COLUMN IF EXISTS versao")
    conn.execute("ALTER TABLE cotacao_itens DROP COLUMN IF EXISTS solicitacao_item_id")