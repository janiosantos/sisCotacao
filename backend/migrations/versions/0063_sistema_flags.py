"""Migração 0063 — Tabela de feature flags.

Armazena o estado (ativo/inativo) das feature flags do sistema, permitindo
alternar comportamentos em runtime (painel Configurações) sem deploy —
rollback comportamental independente do estrutural (item 19 do manual).
"""
from __future__ import annotations

VERSION = 63
RISCO = "rotina"
NAME = "sistema_flags"

# Documentação da mudança de banco (exigida pelo runner desde a v1.6.2).
MUDANCA = {
    "o_que": ["Cria tabela sistema_flags (nome PK, ativo, descricao, atualizado_em)"],
    "porque": [
        "Infraestrutura de feature flags: alternar caminhos de código em runtime "
        "sem desfazer migrações (dívida 6 do manual)"
    ],
}


def guard(conn) -> bool:
    row = conn.execute(
        "SELECT 1 FROM information_schema.tables WHERE table_name='sistema_flags'"
    ).fetchone()
    return row is not None


def forward(conn) -> None:
    autocommit = conn.autocommit
    conn.autocommit = True
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS sistema_flags (
                nome TEXT PRIMARY KEY,
                ativo INTEGER NOT NULL DEFAULT 0,
                descricao TEXT,
                atualizado_em TIMESTAMP NOT NULL DEFAULT now()
            )
            """
        )
    finally:
        conn.autocommit = autocommit


def backward(conn) -> None:
    autocommit = conn.autocommit
    conn.autocommit = True
    try:
        conn.execute("DROP TABLE IF EXISTS sistema_flags")
    finally:
        conn.autocommit = autocommit
