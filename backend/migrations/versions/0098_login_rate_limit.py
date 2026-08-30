"""Migração 0098 — controle persistente de tentativas de login.

Mantém somente chaves de hash e contadores temporários; nenhuma senha ou
identificador bruto é persistido. O controle funciona entre múltiplas
réplicas do backend porque o estado fica no PostgreSQL.
"""
from __future__ import annotations

VERSION = 98
RISCO = "moderada"
NAME = "login_rate_limit"

MUDANCA = {
    "o_que": ["Cria tabela de janela para tentativas de autenticação"],
    "porque": ["Reduz ataques de força bruta sem depender do estado local do processo"],
}


def guard(conn) -> bool:
    row = conn.execute(
        "SELECT 1 FROM information_schema.tables "
        "WHERE table_schema='public' AND table_name='login_rate_limit'"
    ).fetchone()
    return bool(row)


def forward(conn) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS login_rate_limit (
            chave_hash TEXT PRIMARY KEY,
            janela_inicio BIGINT NOT NULL,
            tentativas INTEGER NOT NULL DEFAULT 0,
            atualizado_em TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_login_rate_limit_atualizado "
        "ON login_rate_limit (atualizado_em)"
    )
    conn.commit()


def backward(conn) -> None:
    conn.execute("DROP TABLE IF EXISTS login_rate_limit")
    conn.commit()
