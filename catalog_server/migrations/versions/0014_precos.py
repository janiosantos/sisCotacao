"""
0014 — Tabelas de Preço e Promoções (Fase 3).

Estruturas para gestão de preços:

- `tabelas_preco`      → listas de preço (varejo, atacado, contrato, promocional).
- `tabela_preco_itens` → preço específico de cada variante em cada tabela.
- `promocoes`          → campanhas promocionais (percentual ou valor fixo).
- `promocao_itens`     → itens abrangidos por cada promoção.
"""
from __future__ import annotations

import sqlite3

VERSION = 14
NAME = "Tabelas de preço e promoções"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS tabelas_preco (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    nome         TEXT NOT NULL,
    tipo         TEXT NOT NULL DEFAULT 'varejo'
                 CHECK(tipo IN ('varejo','atacado','contrato','promocional')),
    margem_padrao REAL DEFAULT 0,
    markup       REAL DEFAULT 0,
    ativo        INTEGER NOT NULL DEFAULT 1,
    criado_em    TEXT NOT NULL DEFAULT (datetime('now')),
    atualizado_em TEXT
);

CREATE TABLE IF NOT EXISTS tabela_preco_itens (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    tabela_id    INTEGER NOT NULL REFERENCES tabelas_preco(id) ON DELETE CASCADE,
    variante_id  INTEGER NOT NULL REFERENCES variantes(id),
    preco        REAL NOT NULL,
    margem       REAL,
    ativo        INTEGER NOT NULL DEFAULT 1,
    UNIQUE(tabela_id, variante_id)
);

CREATE TABLE IF NOT EXISTS promocoes (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    nome         TEXT NOT NULL,
    tipo         TEXT NOT NULL CHECK(tipo IN ('percentual','valor_fixo')),
    valor        REAL NOT NULL,
    data_inicio  TEXT,
    data_fim     TEXT,
    ativo        INTEGER NOT NULL DEFAULT 1,
    criado_em    TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS promocao_itens (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    promocao_id       INTEGER NOT NULL REFERENCES promocoes(id) ON DELETE CASCADE,
    variante_id       INTEGER NOT NULL REFERENCES variantes(id),
    preco_promocional REAL,
    UNIQUE(promocao_id, variante_id)
);

CREATE INDEX IF NOT EXISTS idx_tpi_tabela ON tabela_preco_itens(tabela_id);
CREATE INDEX IF NOT EXISTS idx_tpi_variante ON tabela_preco_itens(variante_id);
CREATE INDEX IF NOT EXISTS idx_pi_promocao ON promocao_itens(promocao_id);
"""


def guard(conn: sqlite3.Connection) -> bool:
    try:
        conn.execute("SELECT 1 FROM tabelas_preco LIMIT 1").fetchone()
        conn.execute("SELECT 1 FROM promocoes LIMIT 1").fetchone()
    except sqlite3.OperationalError:
        return False
    return True


def forward(conn: sqlite3.Connection) -> None:
    conn.executescript(_SCHEMA)
    # Tabelas padrão
    if not conn.execute("SELECT 1 FROM tabelas_preco LIMIT 1").fetchone():
        conn.execute("INSERT INTO tabelas_preco (nome, tipo) VALUES ('Tabela Padrão', 'varejo')")


def backward(conn: sqlite3.Connection) -> None:
    conn.executescript(
        "DROP TABLE IF EXISTS promocao_itens;"
        " DROP TABLE IF EXISTS promocoes;"
        " DROP TABLE IF EXISTS tabela_preco_itens;"
        " DROP TABLE IF EXISTS tabelas_preco;"
    )
