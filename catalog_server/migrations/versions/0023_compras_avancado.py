"""
0023 — Compras Avançado: tabela de preços, solicitação e tolerâncias (Fase F).

- `fornecedor_preco`        → preço de compra por fornecedor + variante.
- `fornecedor_preferencial`  → ranking de fornecedor por item.
- `solicitacao_compra`       → solicitação interna com aprovação.
- `solicitacao_itens`        → itens da solicitação.
- `tolerancias_compra`       → tolerâncias por fornecedor.
"""
from __future__ import annotations

import sqlite3

VERSION = 23
NAME = "Compras avançado: preços, solicitação e tolerâncias"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS fornecedor_preco (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    fornecedor_id   INTEGER NOT NULL REFERENCES fornecedores(id) ON DELETE CASCADE,
    variante_id     INTEGER NOT NULL REFERENCES variantes(id),
    preco           REAL NOT NULL,
    prazo_entrega   INTEGER,
    icms            REAL DEFAULT 0,
    ipi             REAL DEFAULT 0,
    moeda           TEXT DEFAULT 'BRL',
    data_validade   TEXT,
    ativo           INTEGER NOT NULL DEFAULT 1,
    criado_em       TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(fornecedor_id, variante_id)
);

CREATE TABLE IF NOT EXISTS fornecedor_preferencial (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    variante_id     INTEGER NOT NULL REFERENCES variantes(id),
    fornecedor_id   INTEGER NOT NULL REFERENCES fornecedores(id),
    ranking         INTEGER NOT NULL DEFAULT 1,
    ultimo_preco    REAL,
    ultimo_prazo    INTEGER,
    criado_em       TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(variante_id, fornecedor_id)
);

CREATE TABLE IF NOT EXISTS solicitacao_compra (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    codigo          TEXT NOT NULL,
    descricao       TEXT DEFAULT '',
    status          TEXT NOT NULL DEFAULT 'rascunho'
                    CHECK(status IN ('rascunho','pendente','aprovada','rejeitada','transformada')),
    data_solicitacao TEXT NOT NULL DEFAULT (date('now')),
    data_aprovacao  TEXT,
    usuario_id      INTEGER REFERENCES usuarios(id),
    aprovador_id    INTEGER REFERENCES usuarios(id),
    observacao      TEXT DEFAULT '',
    criado_em       TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS solicitacao_itens (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    solicitacao_id  INTEGER NOT NULL REFERENCES solicitacao_compra(id) ON DELETE CASCADE,
    variante_id     INTEGER NOT NULL REFERENCES variantes(id),
    quantidade      REAL NOT NULL,
    justificativa   TEXT DEFAULT '',
    criado_em       TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS tolerancias_compra (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    fornecedor_id   INTEGER NOT NULL REFERENCES fornecedores(id) ON DELETE CASCADE,
    tolerancia_preco_pct REAL DEFAULT 10,
    tolerancia_qtd_pct   REAL DEFAULT 10,
    exige_aprovacao      INTEGER NOT NULL DEFAULT 1,
    UNIQUE(fornecedor_id)
);

CREATE INDEX IF NOT EXISTS idx_fp_forn ON fornecedor_preco(fornecedor_id);
CREATE INDEX IF NOT EXISTS idx_fp_var ON fornecedor_preco(variante_id);
CREATE INDEX IF NOT EXISTS idx_fpref_var ON fornecedor_preferencial(variante_id);
CREATE INDEX IF NOT EXISTS idx_sc_status ON solicitacao_compra(status);
"""


def guard(conn: sqlite3.Connection) -> bool:
    try:
        conn.execute("SELECT 1 FROM fornecedor_preco LIMIT 1").fetchone()
    except sqlite3.OperationalError:
        return False
    return True


def forward(conn: sqlite3.Connection) -> None:
    conn.executescript(_SCHEMA)


def backward(conn: sqlite3.Connection) -> None:
    conn.executescript(
        "DROP TABLE IF EXISTS tolerancias_compra;"
        " DROP TABLE IF EXISTS solicitacao_itens;"
        " DROP TABLE IF EXISTS solicitacao_compra;"
        " DROP TABLE IF EXISTS fornecedor_preferencial;"
        " DROP TABLE IF EXISTS fornecedor_preco;"
    )
