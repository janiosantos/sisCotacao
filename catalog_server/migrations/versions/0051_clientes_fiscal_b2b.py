"""
0051 — Campos de endereço estruturado em clientes (NF-e B2B).

A NFC-e (balcão) não exige quase nada do destinatário — mas a NF-e B2B
exige endereço estruturado completo. `clientes` já tinha `ie`,
`contribuinte` ("contribuinte"/"nao_contribuinte") e `c_municipio`
(código IBGE) — faltavam só número, bairro e complemento do endereço
(hoje só existe `endereco`, tratado como logradouro).

Também adiciona uma tabela leve `tecnospeed_empresas` pra registrar, por
CNPJ emitente, se a empresa/certificado já foi cadastrado no PlugNotas —
a API não emite nada pra um CNPJ que não esteja cadastrado lá primeiro.
"""
from __future__ import annotations

import sqlite3

VERSION = 51
NAME = "Endereço estruturado em clientes (NF-e B2B) + registro de empresa Tecnospeed"

_COLUNAS_CLIENTES = {
    "numero": "TEXT",
    "bairro": "TEXT",
    "complemento": "TEXT",
}

_SCHEMA = """
CREATE TABLE IF NOT EXISTS tecnospeed_empresas (
    cpf_cnpj      TEXT PRIMARY KEY,
    certificado_id TEXT,
    empresa_cadastrada INTEGER NOT NULL DEFAULT 0,
    atualizado_em TEXT NOT NULL DEFAULT (datetime('now'))
);
"""


def guard(conn: sqlite3.Connection) -> bool:
    cols = {r[1] for r in conn.execute("PRAGMA table_info(clientes)").fetchall()}
    if "numero" not in cols or "bairro" not in cols:
        return False
    try:
        conn.execute("SELECT 1 FROM tecnospeed_empresas LIMIT 1").fetchone()
    except sqlite3.OperationalError:
        return False
    return True


def forward(conn: sqlite3.Connection) -> None:
    existing = {r[1] for r in conn.execute("PRAGMA table_info(clientes)").fetchall()}
    for col, ddl in _COLUNAS_CLIENTES.items():
        if col not in existing:
            conn.execute(f"ALTER TABLE clientes ADD COLUMN {col} {ddl}")
    conn.executescript(_SCHEMA)


def backward(conn: sqlite3.Connection) -> None:
    conn.executescript("DROP TABLE IF EXISTS tecnospeed_empresas;")
