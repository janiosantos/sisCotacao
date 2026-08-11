"""0010 — Orçamentos de venda ao cliente (PDV).

Tabelas para o fluxo de orçamento de venda: `orcamentos` guarda cabeçalho
(cliente, validade, status, totais) e `orcamento_itens` os itens em formato
livre (nome/sku/marca/preço), desvinculado do catálogo — o orçamento deve
permanecer estável mesmo se o produto mudar no catálogo.
"""
from __future__ import annotations

import sqlite3

VERSION = 10
NAME = "Orçamentos de venda ao cliente (PDV)"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS orcamentos (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    numero       TEXT NOT NULL UNIQUE,
    cliente      TEXT NOT NULL DEFAULT '',
    contato      TEXT NOT NULL DEFAULT '',
    validade_dias INTEGER NOT NULL DEFAULT 7,
    observacoes  TEXT NOT NULL DEFAULT '',
    status       TEXT NOT NULL DEFAULT 'rascunho',
    desconto     REAL NOT NULL DEFAULT 0,
    subtotal     REAL NOT NULL DEFAULT 0,
    total        REAL NOT NULL DEFAULT 0,
    criado_em    TEXT NOT NULL DEFAULT (datetime('now')),
    atualizado_em TEXT
);

CREATE TABLE IF NOT EXISTS orcamento_itens (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    orcamento_id     INTEGER NOT NULL REFERENCES orcamentos(id) ON DELETE CASCADE,
    produto_id       INTEGER,
    nome             TEXT NOT NULL,
    sku              TEXT NOT NULL DEFAULT '',
    marca            TEXT NOT NULL DEFAULT '',
    especificacao    TEXT NOT NULL DEFAULT '',
    quantidade       REAL NOT NULL DEFAULT 1,
    preco_unitario   REAL NOT NULL DEFAULT 0,
    desconto_percentual REAL NOT NULL DEFAULT 0,
    subtotal         REAL NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_orcamento_itens_orcamento
    ON orcamento_itens(orcamento_id);
"""


def guard(conn: sqlite3.Connection) -> bool:
    try:
        conn.execute("SELECT 1 FROM orcamentos LIMIT 1").fetchone()
        conn.execute("SELECT 1 FROM orcamento_itens LIMIT 1").fetchone()
    except sqlite3.OperationalError:
        return False
    return True


def forward(conn: sqlite3.Connection) -> None:
    conn.executescript(_SCHEMA)


def backward(conn: sqlite3.Connection) -> None:
    conn.executescript(
        "DROP TABLE IF EXISTS orcamento_itens; DROP TABLE IF EXISTS orcamentos;"
    )