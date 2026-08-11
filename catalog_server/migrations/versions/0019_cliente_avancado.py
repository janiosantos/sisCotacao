"""
0019 — Cliente Avançado: endereços, contatos e apoio comercial (Fase B).

- `cliente_enderecos` → múltiplos endereços (cobrança, entrega, faturamento).
- `cliente_contatos`  → contatos por cliente (nome, cargo, telefone, email).
- `cliente_apoio_comercial` → condições de pagamento, tabela de preço, limite, transportadora.
- `cliente_apoio_fiscal`    → CFOP, CST, alíquotas por cliente.
"""
from __future__ import annotations

import sqlite3

VERSION = 19
NAME = "Cliente avançado: endereços, contatos, apoio comercial e fiscal"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS cliente_enderecos (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    cliente_id  INTEGER NOT NULL REFERENCES clientes(id) ON DELETE CASCADE,
    tipo        TEXT NOT NULL CHECK(tipo IN ('cobranca','entrega','faturamento')),
    cep         TEXT DEFAULT '',
    logradouro  TEXT DEFAULT '',
    numero      TEXT DEFAULT '',
    complemento TEXT DEFAULT '',
    bairro      TEXT DEFAULT '',
    cidade      TEXT DEFAULT '',
    uf          TEXT DEFAULT '',
    criado_em   TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS cliente_contatos (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    cliente_id  INTEGER NOT NULL REFERENCES clientes(id) ON DELETE CASCADE,
    nome        TEXT NOT NULL,
    cargo       TEXT DEFAULT '',
    telefone    TEXT DEFAULT '',
    email       TEXT DEFAULT '',
    criado_em   TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS cliente_apoio_comercial (
    id                   INTEGER PRIMARY KEY AUTOINCREMENT,
    cliente_id           INTEGER NOT NULL REFERENCES clientes(id) ON DELETE CASCADE UNIQUE,
    condicao_pagamento_id INTEGER,
    tabela_preco_id      INTEGER REFERENCES tabelas_preco(id),
    limite_credito       REAL DEFAULT 0,
    transportadora       TEXT DEFAULT '',
    criado_em            TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS cliente_apoio_fiscal (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    cliente_id     INTEGER NOT NULL REFERENCES clientes(id) ON DELETE CASCADE UNIQUE,
    cfop_padrao    TEXT DEFAULT '',
    cst_icms       TEXT DEFAULT '',
    cst_pis        TEXT DEFAULT '',
    cst_cofins     TEXT DEFAULT '',
    aliquota_icms  REAL DEFAULT 0,
    aliquota_pis   REAL DEFAULT 0,
    aliquota_cofins REAL DEFAULT 0,
    criado_em      TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_cli_end_cliente ON cliente_enderecos(cliente_id);
CREATE INDEX IF NOT EXISTS idx_cli_cont_cliente ON cliente_contatos(cliente_id);
"""


def guard(conn: sqlite3.Connection) -> bool:
    try:
        conn.execute("SELECT 1 FROM cliente_enderecos LIMIT 1").fetchone()
        conn.execute("SELECT 1 FROM cliente_contatos LIMIT 1").fetchone()
    except sqlite3.OperationalError:
        return False
    return True


def forward(conn: sqlite3.Connection) -> None:
    conn.executescript(_SCHEMA)


def backward(conn: sqlite3.Connection) -> None:
    conn.executescript(
        "DROP TABLE IF EXISTS cliente_apoio_fiscal;"
        " DROP TABLE IF EXISTS cliente_apoio_comercial;"
        " DROP TABLE IF EXISTS cliente_contatos;"
        " DROP TABLE IF EXISTS cliente_enderecos;"
    )
