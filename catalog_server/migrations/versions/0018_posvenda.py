"""
0018 — Pós-venda (Fase 5).

CRM e acompanhamento de clientes:

- `cliente_interacao` → histórico de interações (ligação, visita, email, WhatsApp, follow-up).
- `garantia`          → termos de garantia por venda/produto.
"""
from __future__ import annotations

import sqlite3

VERSION = 18
NAME = "Pós-venda: interações com clientes e garantia"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS cliente_interacao (
    id                   INTEGER PRIMARY KEY AUTOINCREMENT,
    cliente_id           INTEGER REFERENCES clientes(id) ON DELETE CASCADE,
    cliente_nome         TEXT NOT NULL,
    tipo                 TEXT NOT NULL
                         CHECK(tipo IN ('ligacao','visita','email','whatsapp','follow_up','outro')),
    descricao            TEXT NOT NULL DEFAULT '',
    data_contato         TEXT NOT NULL,
    data_proximo_contato TEXT,
    orcamento_id         INTEGER REFERENCES orcamentos(id),
    usuario_id           INTEGER REFERENCES usuarios(id),
    criado_em            TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS garantia (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    cliente_nome      TEXT NOT NULL DEFAULT '',
    cliente_id        INTEGER REFERENCES clientes(id),
    orcamento_id      INTEGER REFERENCES orcamentos(id),
    variante_id       INTEGER REFERENCES variantes(id),
    produto_nome      TEXT NOT NULL DEFAULT '',
    data_venda        TEXT,
    data_inicio       TEXT NOT NULL,
    data_fim          TEXT NOT NULL,
    dias              INTEGER NOT NULL DEFAULT 90,
    descricao         TEXT DEFAULT '',
    observacao        TEXT DEFAULT '',
    status            TEXT NOT NULL DEFAULT 'ativa'
                      CHECK(status IN ('ativa','vencida','acionada','cancelada')),
    criado_em         TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_interacao_cliente ON cliente_interacao(cliente_id);
CREATE INDEX IF NOT EXISTS idx_interacao_data ON cliente_interacao(data_contato);
CREATE INDEX IF NOT EXISTS idx_garantia_cliente ON garantia(cliente_id);
CREATE INDEX IF NOT EXISTS idx_garantia_status ON garantia(status);
"""


def guard(conn: sqlite3.Connection) -> bool:
    try:
        conn.execute("SELECT 1 FROM cliente_interacao LIMIT 1").fetchone()
        conn.execute("SELECT 1 FROM garantia LIMIT 1").fetchone()
    except sqlite3.OperationalError:
        return False
    return True


def forward(conn: sqlite3.Connection) -> None:
    conn.executescript(_SCHEMA)


def backward(conn: sqlite3.Connection) -> None:
    conn.executescript(
        "DROP TABLE IF EXISTS garantia;"
        " DROP TABLE IF EXISTS cliente_interacao;"
    )
