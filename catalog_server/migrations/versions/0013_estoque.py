"""
0013 — Módulo de Estoque (Fase 2).

Tabelas de controle de estoque físico (inspirado nos módulos "Estoque" e
"Tabela de preços" da doc do Bravo Gestor):

- `depositos`          → localizações físicas (depósitos/lojas/estoques).
- `estoque_saldo`      → saldo atual por depósito + variante.
- `estoque_movimento`  → movimentação (entrada/saída/ajuste/transferência/inventário).
- `lotes`              → controle por lote com validade.
- `variantes.ncm`      → código NCM fiscal para produtos.
"""
from __future__ import annotations

import sqlite3

VERSION = 13
NAME = "Módulo de Estoque: depósitos, saldo, movimento, lotes e NCM"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS depositos (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    nome       TEXT NOT NULL UNIQUE,
    ativo      INTEGER NOT NULL DEFAULT 1,
    criado_em  TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS estoque_saldo (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    deposito_id    INTEGER NOT NULL REFERENCES depositos(id),
    variante_id    INTEGER NOT NULL REFERENCES variantes(id),
    quantidade     REAL NOT NULL DEFAULT 0,
    reserva        REAL NOT NULL DEFAULT 0,
    atualizado_em  TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(deposito_id, variante_id)
);

CREATE TABLE IF NOT EXISTS estoque_movimento (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    deposito_id      INTEGER NOT NULL REFERENCES depositos(id),
    variante_id      INTEGER NOT NULL REFERENCES variantes(id),
    tipo             TEXT NOT NULL CHECK(tipo IN ('entrada','saida','ajuste','transferencia','inventario')),
    quantidade       REAL NOT NULL,
    saldo_anterior   REAL NOT NULL DEFAULT 0,
    saldo_posterior  REAL NOT NULL DEFAULT 0,
    documento        TEXT,
    observacao       TEXT,
    lote_id          INTEGER REFERENCES lotes(id),
    usuario_id       INTEGER REFERENCES usuarios(id),
    criado_em        TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS lotes (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    deposito_id     INTEGER NOT NULL REFERENCES depositos(id),
    variante_id     INTEGER NOT NULL REFERENCES variantes(id),
    codigo          TEXT NOT NULL,
    data_fabricacao TEXT,
    data_validade   TEXT,
    quantidade      REAL NOT NULL DEFAULT 0,
    criado_em       TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_estoque_saldo_dep_var ON estoque_saldo(deposito_id, variante_id);
CREATE INDEX IF NOT EXISTS idx_estoque_movimento_dep ON estoque_movimento(deposito_id);
CREATE INDEX IF NOT EXISTS idx_estoque_movimento_var ON estoque_movimento(variante_id);
CREATE INDEX IF NOT EXISTS idx_estoque_movimento_tipo ON estoque_movimento(tipo);
CREATE INDEX IF NOT EXISTS idx_lotes_dep_var ON lotes(deposito_id, variante_id);
"""


def guard(conn: sqlite3.Connection) -> bool:
    try:
        conn.execute("SELECT 1 FROM depositos LIMIT 1").fetchone()
        conn.execute("SELECT 1 FROM estoque_saldo LIMIT 1").fetchone()
        conn.execute("SELECT 1 FROM estoque_movimento LIMIT 1").fetchone()
        conn.execute("SELECT 1 FROM lotes LIMIT 1").fetchone()
    except sqlite3.OperationalError:
        return False
    return True


def forward(conn: sqlite3.Connection) -> None:
    conn.executescript(_SCHEMA)
    # Adiciona coluna ncm na tabela variantes (se não existir)
    try:
        cols = {r[1] for r in conn.execute("PRAGMA table_info(variantes)").fetchall()}
    except sqlite3.OperationalError:
        cols = set()
    if "ncm" not in cols:
        conn.execute("ALTER TABLE variantes ADD COLUMN ncm TEXT DEFAULT ''")
    # Depósito padrão "Matriz"
    if not conn.execute("SELECT 1 FROM depositos LIMIT 1").fetchone():
        conn.execute("INSERT INTO depositos (nome) VALUES ('Matriz')")


def backward(conn: sqlite3.Connection) -> None:
    conn.executescript(
        "DROP TABLE IF EXISTS lotes;"
        " DROP TABLE IF EXISTS estoque_movimento;"
        " DROP TABLE IF EXISTS estoque_saldo;"
        " DROP TABLE IF EXISTS depositos;"
    )
    try:
        cols = {r[1] for r in conn.execute("PRAGMA table_info(variantes)").fetchall()}
        if "ncm" in cols:
            conn.execute("ALTER TABLE variantes DROP COLUMN ncm")
    except sqlite3.OperationalError:
        pass
