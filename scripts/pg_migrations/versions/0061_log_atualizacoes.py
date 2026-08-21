"""Migração 0061 — Tabela de log de atualizações do sistema.

Registra cada aplicação de migrações (origem deploy/painel), com versão do
app, versão do schema antes/depois, total aplicado, usuário e erro (se houve).
Alimenta o "Histórico" do Painel de Atualizações.
"""
from __future__ import annotations

VERSION = 61
RISCO = "rotina"
NAME = "sistema_atualizacoes"


def guard(conn) -> bool:
    row = conn.execute(
        "SELECT 1 FROM information_schema.tables WHERE table_name='sistema_atualizacoes'"
    ).fetchone()
    return row is not None


def forward(conn) -> None:
    autocommit = conn.autocommit
    conn.autocommit = True
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS sistema_atualizacoes (
                id SERIAL PRIMARY KEY,
                executado_em TIMESTAMP NOT NULL DEFAULT now(),
                nivel TEXT NOT NULL,
                versao_app TEXT NOT NULL,
                schema_antes INTEGER NOT NULL,
                schema_depois INTEGER NOT NULL,
                total_aplicadas INTEGER NOT NULL DEFAULT 0,
                detalhes JSONB,
                origem TEXT NOT NULL DEFAULT 'deploy',
                usuario TEXT,
                erro TEXT
            )
            """
        )
    finally:
        conn.autocommit = autocommit


def backward(conn) -> None:
    autocommit = conn.autocommit
    conn.autocommit = True
    try:
        conn.execute("DROP TABLE IF EXISTS sistema_atualizacoes")
    finally:
        conn.autocommit = autocommit
