"""
0017 — Bancos (Fase 7).

Contas bancárias e movimentação financeira:

- `contas_bancarias`   → cadastro de contas correntes/investimento.
- `movimento_bancario` → extrato por conta (crédito, débito, transferência).
"""
from __future__ import annotations

import sqlite3

VERSION = 17
NAME = "Bancos: contas bancárias e movimento"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS contas_bancarias (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    nome           TEXT NOT NULL,
    banco          TEXT NOT NULL DEFAULT '000',
    agencia        TEXT DEFAULT '',
    conta          TEXT DEFAULT '',
    digito         TEXT DEFAULT '',
    saldo_inicial  REAL NOT NULL DEFAULT 0,
    saldo_atual    REAL NOT NULL DEFAULT 0,
    ativo          INTEGER NOT NULL DEFAULT 1,
    criado_em      TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS movimento_bancario (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    conta_id          INTEGER NOT NULL REFERENCES contas_bancarias(id) ON DELETE CASCADE,
    tipo              TEXT NOT NULL CHECK(tipo IN ('credito','debito','transferencia')),
    valor             REAL NOT NULL,
    data_movimento    TEXT NOT NULL,
    data_conciliacao  TEXT,
    descricao         TEXT NOT NULL DEFAULT '',
    documento         TEXT DEFAULT '',
    categoria         TEXT DEFAULT '',
    plano_conta_id    INTEGER REFERENCES plano_de_contas(id),
    conciliado        INTEGER NOT NULL DEFAULT 0,
    criado_em         TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_mov_bancario_conta ON movimento_bancario(conta_id);
CREATE INDEX IF NOT EXISTS idx_mov_bancario_data ON movimento_bancario(data_movimento);
CREATE INDEX IF NOT EXISTS idx_mov_bancario_conc ON movimento_bancario(conciliado);
"""


def guard(conn: sqlite3.Connection) -> bool:
    try:
        conn.execute("SELECT 1 FROM contas_bancarias LIMIT 1").fetchone()
        conn.execute("SELECT 1 FROM movimento_bancario LIMIT 1").fetchone()
    except sqlite3.OperationalError:
        return False
    return True


def forward(conn: sqlite3.Connection) -> None:
    conn.executescript(_SCHEMA)


def backward(conn: sqlite3.Connection) -> None:
    conn.executescript(
        "DROP TABLE IF EXISTS movimento_bancario;"
        " DROP TABLE IF EXISTS contas_bancarias;"
    )
