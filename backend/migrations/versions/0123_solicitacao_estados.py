"""Migração 0123 — solicitação de compra: prioridade, origem, depósito, prazo e máquina de estados (COM-007)."""
from __future__ import annotations

VERSION = 123
RISCO = "baixa"  # Expand: colunas novas
NAME = "solicitacao_estados"

MUDANCA = {
    "o_que": [
        "solicitacao_compra + prioridade, origem, centro_custo, deposito_id, prazo_desejado, data_enviada",
        "solicitacao_itens + unidade, necessidade, origem_sugestao",
    ],
    "porque": [
        "Máquina rascunho→enviada→aprovada→cotando→convertida→cancelada; aprovada não edita sem nova versão (COM-007)",
        "Itens carregam unidade, necessidade, justificativa e origem da sugestão",
    ],
}


def guard(conn) -> bool:
    row = conn.execute(
        "SELECT 1 FROM information_schema.columns "
        "WHERE table_name='solicitacao_compra' AND column_name='prioridade'"
    ).fetchone()
    return bool(row)


def forward(conn) -> None:
    conn.execute("ALTER TABLE solicitacao_compra ADD COLUMN IF NOT EXISTS prioridade VARCHAR(20) NOT NULL DEFAULT 'media'")
    conn.execute("ALTER TABLE solicitacao_compra ADD COLUMN IF NOT EXISTS origem VARCHAR(20) NOT NULL DEFAULT 'manual'")
    conn.execute("ALTER TABLE solicitacao_compra ADD COLUMN IF NOT EXISTS centro_custo VARCHAR(40)")
    conn.execute("ALTER TABLE solicitacao_compra ADD COLUMN IF NOT EXISTS deposito_id INTEGER")
    conn.execute("ALTER TABLE solicitacao_compra ADD COLUMN IF NOT EXISTS prazo_desejado DATE")
    conn.execute("ALTER TABLE solicitacao_compra ADD COLUMN IF NOT EXISTS data_enviada TIMESTAMPTZ")
    conn.execute("ALTER TABLE solicitacao_itens ADD COLUMN IF NOT EXISTS unidade VARCHAR(10) NOT NULL DEFAULT 'UN'")
    conn.execute("ALTER TABLE solicitacao_itens ADD COLUMN IF NOT EXISTS necessidade NUMERIC(14,3)")
    conn.execute("ALTER TABLE solicitacao_itens ADD COLUMN IF NOT EXISTS origem_sugestao VARCHAR(40)")
    conn.commit()


def backward(conn) -> None:
    for col in ("prioridade", "origem", "centro_custo", "deposito_id", "prazo_desejado", "data_enviada"):
        conn.execute(f"ALTER TABLE solicitacao_compra DROP COLUMN IF EXISTS {col}")
    for col in ("unidade", "necessidade", "origem_sugestao"):
        conn.execute(f"ALTER TABLE solicitacao_itens DROP COLUMN IF EXISTS {col}")