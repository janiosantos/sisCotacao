"""Migração 0102 — claim/lease para processamento concorrente do outbox.

Expand-only: adiciona metadados para que múltiplos workers não processem a
mesma linha simultaneamente e para recuperar linhas abandonadas por um worker
que foi encerrado durante o processamento.
"""
from __future__ import annotations

VERSION = 102
RISCO = "moderada"
NAME = "outbox_claim"

MUDANCA = {
    "o_que": ["outbox: estado processando e lease do worker"],
    "porque": [
        "Evita processamento duplicado quando há mais de um worker ou execução manual",
        "Permite recuperar itens abandonados após queda do worker",
    ],
}


def guard(conn) -> bool:
    row = conn.execute(
        "SELECT COUNT(*) AS n FROM information_schema.columns "
        "WHERE table_schema='public' AND table_name='outbox' "
        "AND column_name IN ('processando_em', 'processando_por')"
    ).fetchone()
    return int(row["n"] if row else 0) == 2


def forward(conn) -> None:
    conn.execute(
        "ALTER TABLE outbox ADD COLUMN IF NOT EXISTS processando_em TIMESTAMPTZ"
    )
    conn.execute(
        "ALTER TABLE outbox ADD COLUMN IF NOT EXISTS processando_por TEXT"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_outbox_processando_em "
        "ON outbox (status, processando_em)"
    )
    conn.commit()


def backward(conn) -> None:
    conn.execute("DROP INDEX IF EXISTS idx_outbox_processando_em")
    conn.execute("ALTER TABLE outbox DROP COLUMN IF EXISTS processando_em")
    conn.execute("ALTER TABLE outbox DROP COLUMN IF EXISTS processando_por")
    conn.commit()
