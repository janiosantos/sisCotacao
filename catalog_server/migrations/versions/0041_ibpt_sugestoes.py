"""0041 - Sugestões de NCM (IBPT) por produto.

`ibpt_sugestoes` guarda a sugestão automática de NCM (casada por nome/descrição
com a tabela IBPT) para revisão antes de aplicar em `variantes.ncm`.
"""
from __future__ import annotations

import sqlite3

VERSION = 41
NAME = "Sugestões de NCM (IBPT) por produto"

_SQL = """
CREATE TABLE IF NOT EXISTS ibpt_sugestoes (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    variante_id  INTEGER NOT NULL REFERENCES variantes(id) ON DELETE CASCADE,
    ncm          TEXT NOT NULL,
    descricao    TEXT DEFAULT '',
    confianca    REAL NOT NULL DEFAULT 0,
    status       TEXT NOT NULL DEFAULT 'pendente'
                 CHECK(status IN ('pendente','aplicada','rejeitada')),
    criado_em    TEXT NOT NULL DEFAULT (datetime('now')),
    aplicado_em  TEXT,
    UNIQUE(variante_id)
);

CREATE INDEX IF NOT EXISTS idx_ibpt_sug_status ON ibpt_sugestoes(status);
"""


def guard(conn: sqlite3.Connection) -> bool:
    try:
        conn.execute("SELECT 1 FROM ibpt_sugestoes LIMIT 1").fetchone()
    except sqlite3.OperationalError:
        return False
    return True


def forward(conn: sqlite3.Connection) -> None:
    conn.executescript(_SQL)


def backward(conn: sqlite3.Connection) -> None:
    conn.execute("DROP TABLE IF EXISTS ibpt_sugestoes")
