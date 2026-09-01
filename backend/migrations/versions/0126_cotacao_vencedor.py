"""Migração 0126 — comparação de propostas: vencedor por item com justificativa (COM-009)."""
from __future__ import annotations

VERSION = 126
RISCO = "baixa"  # Expand: colunas novas
NAME = "cotacao_vencedor"

MUDANCA = {
    "o_que": [
        "cotacao_precos + vencedor (bool), justificativa_vencedor, data_decisao, decidido_por",
        "cotacoes + decisao_concluida (marcar quando todos os itens tiverem vencedor)",
    ],
    "porque": [
        "Comparação não escolhe só pelo menor preço; usuário justifica vencedor (COM-009)",
    ],
}


def guard(conn) -> bool:
    row = conn.execute(
        "SELECT 1 FROM information_schema.columns "
        "WHERE table_name='cotacao_precos' AND column_name='vencedor'"
    ).fetchone()
    return bool(row)


def forward(conn) -> None:
    conn.execute("ALTER TABLE cotacao_precos ADD COLUMN IF NOT EXISTS vencedor BOOLEAN NOT NULL DEFAULT FALSE")
    conn.execute("ALTER TABLE cotacao_precos ADD COLUMN IF NOT EXISTS justificativa_vencedor TEXT")
    conn.execute("ALTER TABLE cotacao_precos ADD COLUMN IF NOT EXISTS data_decisao TIMESTAMPTZ")
    conn.execute("ALTER TABLE cotacao_precos ADD COLUMN IF NOT EXISTS decidido_por INTEGER")
    conn.execute("ALTER TABLE cotacoes ADD COLUMN IF NOT EXISTS decisao_concluida BOOLEAN NOT NULL DEFAULT FALSE")
    conn.commit()


def backward(conn) -> None:
    for col in ("vencedor", "justificativa_vencedor", "data_decisao", "decidido_por"):
        conn.execute(f"ALTER TABLE cotacao_precos DROP COLUMN IF EXISTS {col}")
    conn.execute("ALTER TABLE cotacoes DROP COLUMN IF EXISTS decisao_concluida")