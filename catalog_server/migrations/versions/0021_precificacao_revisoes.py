"""
0021 — Precificação com Revisões (Fase D).

- `precificacao_revisoes` → versões de preço com data validade e situação (aberta/fechada).
  Cada revisão vincula-se a uma tabela de preço e a um cliente opcional.
"""
from __future__ import annotations

import sqlite3

VERSION = 21
NAME = "Precificação com revisões e margem"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS precificacao_revisoes (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    tabela_id       INTEGER NOT NULL REFERENCES tabelas_preco(id) ON DELETE CASCADE,
    codigo          TEXT NOT NULL,
    descricao       TEXT DEFAULT '',
    data_cadastro   TEXT NOT NULL DEFAULT (date('now')),
    data_validade   TEXT,
    situacao        TEXT NOT NULL DEFAULT 'aberta' CHECK(situacao IN ('aberta','fechada')),
    cliente_id      INTEGER REFERENCES clientes(id),
    criado_em       TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_revisao_tabela ON precificacao_revisoes(tabela_id);
"""


def guard(conn: sqlite3.Connection) -> bool:
    try:
        conn.execute("SELECT 1 FROM precificacao_revisoes LIMIT 1").fetchone()
    except sqlite3.OperationalError:
        return False
    return True


def forward(conn: sqlite3.Connection) -> None:
    conn.executescript(_SCHEMA)


def backward(conn: sqlite3.Connection) -> None:
    conn.executescript("DROP TABLE IF EXISTS precificacao_revisoes;")
