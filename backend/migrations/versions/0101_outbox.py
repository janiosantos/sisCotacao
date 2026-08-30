"""Migração 0101 — outbox transacional (P5).

Cria a tabela `outbox` para operações assíncronas confiáveis: uma linha é
gravada NA MESMA transação do fato de negócio e processada pelo worker RQ,
com retry/backoff, dead-letter e chave de idempotência (duplicatas ignoradas).
"""
from __future__ import annotations

VERSION = 101
RISCO = "moderada"
NAME = "outbox"

MUDANCA = {
    "o_que": ["Cria tabela outbox para processamento assíncrono confiável (worker RQ)"],
    "porque": [
        "Garante que operações externas (webhooks, imagens, integrações) não se percam em falha de request/processo",
        "Retry com backoff, dead-letter e idempotência por chave",
    ],
}


def guard(conn) -> bool:
    row = conn.execute(
        "SELECT 1 FROM information_schema.tables "
        "WHERE table_schema='public' AND table_name='outbox'"
    ).fetchone()
    return bool(row)


def forward(conn) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS outbox (
            id BIGSERIAL PRIMARY KEY,
            topico TEXT NOT NULL,
            payload TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pendente',  -- pendente | ok | erro | morta
            tentativas INTEGER NOT NULL DEFAULT 0,
            proxima_tentativa TIMESTAMPTZ,
            ultimo_erro TEXT,
            idempotencia_key TEXT UNIQUE,
            criado_em TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            atualizado_em TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_outbox_pendentes "
        "ON outbox (status, proxima_tentativa)"
    )
    conn.commit()


def backward(conn) -> None:
    conn.execute("DROP TABLE IF EXISTS outbox")