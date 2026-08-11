"""
0020 — Aprofundamento Financeiro: condições pagamento, centros custo (Fase A).

- `condicoes_pagamento` → formas de pagamento com parcelas (à vista, 30/60/90, entrada+saldo).
- `condicao_parcelas`   → cada parcela de uma condição (dias, percentual).
- `centros_custo`       → centros de custo para rateio financeiro.
- `adiantamentos`       → adiantamentos de clientes e fornecedores.
"""
from __future__ import annotations

import sqlite3

VERSION = 20
NAME = "Condições de pagamento, centros de custo e adiantamentos"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS condicoes_pagamento (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    nome        TEXT NOT NULL,
    descricao   TEXT DEFAULT '',
    ativo       INTEGER NOT NULL DEFAULT 1,
    criado_em   TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS condicao_parcelas (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    condicao_id     INTEGER NOT NULL REFERENCES condicoes_pagamento(id) ON DELETE CASCADE,
    sequencia       INTEGER NOT NULL,
    dias            INTEGER NOT NULL DEFAULT 0,
    percentual      REAL NOT NULL DEFAULT 100,
    criado_em       TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS centros_custo (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    codigo      TEXT NOT NULL UNIQUE,
    nome        TEXT NOT NULL,
    ativo       INTEGER NOT NULL DEFAULT 1,
    criado_em   TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS adiantamentos (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    tipo            TEXT NOT NULL CHECK(tipo IN ('cliente','fornecedor')),
    pessoa_id       INTEGER,
    pessoa_nome     TEXT NOT NULL,
    valor           REAL NOT NULL,
    saldo           REAL NOT NULL,
    data_adiantamento TEXT NOT NULL,
    data_baixa      TEXT,
    observacao      TEXT DEFAULT '',
    criado_em       TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_adiantamentos_tipo ON adiantamentos(tipo);
"""


def guard(conn: sqlite3.Connection) -> bool:
    try:
        conn.execute("SELECT 1 FROM condicoes_pagamento LIMIT 1").fetchone()
        conn.execute("SELECT 1 FROM centros_custo LIMIT 1").fetchone()
    except sqlite3.OperationalError:
        return False
    return True


def forward(conn: sqlite3.Connection) -> None:
    conn.executescript(_SCHEMA)
    # Condições padrão
    if not conn.execute("SELECT 1 FROM condicoes_pagamento LIMIT 1").fetchone():
        conn.execute("INSERT INTO condicoes_pagamento (nome, descricao) VALUES ('À Vista', 'Pagamento à vista')")
        conn.execute("INSERT INTO condicao_parcelas (condicao_id, sequencia, dias, percentual) VALUES (1, 1, 0, 100)")

        conn.execute("INSERT INTO condicoes_pagamento (nome, descricao) VALUES ('30 dias', 'Pagamento em 30 dias')")
        conn.execute("INSERT INTO condicao_parcelas (condicao_id, sequencia, dias, percentual) VALUES (2, 1, 30, 100)")

        conn.execute("INSERT INTO condicoes_pagamento (nome, descricao) VALUES ('30/60 dias', 'Parcelado em 2x')")
        conn.execute("INSERT INTO condicao_parcelas (condicao_id, sequencia, dias, percentual) VALUES (3, 1, 30, 50)")
        conn.execute("INSERT INTO condicao_parcelas (condicao_id, sequencia, dias, percentual) VALUES (3, 2, 60, 50)")

        conn.execute("INSERT INTO condicoes_pagamento (nome, descricao) VALUES ('30/60/90 dias', 'Parcelado em 3x')")
        conn.execute("INSERT INTO condicao_parcelas (condicao_id, sequencia, dias, percentual) VALUES (4, 1, 30, 33.33)")
        conn.execute("INSERT INTO condicao_parcelas (condicao_id, sequencia, dias, percentual) VALUES (4, 2, 60, 33.33)")
        conn.execute("INSERT INTO condicao_parcelas (condicao_id, sequencia, dias, percentual) VALUES (4, 3, 90, 33.34)")
    # Centros de custo padrão
    if not conn.execute("SELECT 1 FROM centros_custo LIMIT 1").fetchone():
        conn.executemany(
            "INSERT INTO centros_custo (codigo, nome) VALUES (?,?)",
            [("ADM", "Administrativo"), ("COM", "Comercial"), ("FIN", "Financeiro"),
             ("LOG", "Logística"), ("PROD", "Produção"), ("TI", "Tecnologia")],
        )


def backward(conn: sqlite3.Connection) -> None:
    conn.executescript(
        "DROP TABLE IF EXISTS adiantamentos;"
        " DROP TABLE IF EXISTS condicao_parcelas;"
        " DROP TABLE IF EXISTS condicoes_pagamento;"
        " DROP TABLE IF EXISTS centros_custo;"
    )
