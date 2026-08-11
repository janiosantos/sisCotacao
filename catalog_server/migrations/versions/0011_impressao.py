"""0011 — Retaguarda de impressão (PDV/térmica).

`impressao_config` guarda singleton de destino da impressora (host/porta,
largura do papel, impressão automática ao salvar). `impressao_fila` é a fila
de trabalhos: cada registro é um cupom a imprimir em ESC/POS com estado
(pendente/processando/ok/erro) para a retaguarda processar dinamicamente.
"""
from __future__ import annotations

import sqlite3

VERSION = 11
NAME = "Retaguarda de impressão térmica"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS impressao_config (
    id            INTEGER PRIMARY KEY CHECK (id = 1),
    host          TEXT NOT NULL DEFAULT '127.0.0.1',
    porta         INTEGER NOT NULL DEFAULT 9100,
    papel_mm      INTEGER NOT NULL DEFAULT 80,
    auto_impressao INTEGER NOT NULL DEFAULT 0,
    ativo         INTEGER NOT NULL DEFAULT 1,
    atualizado_em TEXT
);

CREATE TABLE IF NOT EXISTS impressao_fila (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    tipo          TEXT NOT NULL DEFAULT 'orcamento',
    referencia    TEXT NOT NULL DEFAULT '',
    payload       TEXT NOT NULL,
    status        TEXT NOT NULL DEFAULT 'pendente',
    erro          TEXT,
    criado_em     TEXT NOT NULL DEFAULT (datetime('now')),
    processado_em TEXT
);

CREATE INDEX IF NOT EXISTS idx_impressao_fila_status
    ON impressao_fila(status);
"""


def guard(conn: sqlite3.Connection) -> bool:
    try:
        conn.execute("SELECT 1 FROM impressao_fila LIMIT 1").fetchone()
        conn.execute("SELECT 1 FROM impressao_config LIMIT 1").fetchone()
    except sqlite3.OperationalError:
        return False
    return True


def forward(conn: sqlite3.Connection) -> None:
    conn.executescript(_SCHEMA)


def backward(conn: sqlite3.Connection) -> None:
    conn.executescript(
        "DROP TABLE IF EXISTS impressao_fila; DROP TABLE IF EXISTS impressao_config;"
    )