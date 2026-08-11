"""
0025 — Fiscal Avançado: emitente, NF-e e IBPT (Fase G).

- `emitente`         → dados fiscais da empresa (CNPJ, IE, CNAE, regime, token Focus).
- `nfe_saida`        → NF-e de saída emitidas (status, chave, XML).
- `nfe_entrada`      → NF-e de entrada recebidas (chave, fornecedor, XML).
- `ibpt`             → tabela IBPT (carga tributária por NCM).
"""
from __future__ import annotations

import sqlite3

VERSION = 25
NAME = "Fiscal avançado: emitente, NF-e e IBPT"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS emitente (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    razao_social        TEXT NOT NULL,
    nome_fantasia       TEXT DEFAULT '',
    cnpj                TEXT NOT NULL,
    ie                  TEXT DEFAULT '',
    im                  TEXT DEFAULT '',
    regime_tributario   TEXT DEFAULT 'simples_nacional'
                        CHECK(regime_tributario IN ('simples_nacional','lucro_presumido','lucro_real')),
    cnae_principal      TEXT DEFAULT '',
    cnae_secundario     TEXT DEFAULT '',
    logradouro          TEXT DEFAULT '',
    numero              TEXT DEFAULT '',
    bairro              TEXT DEFAULT '',
    cep                 TEXT DEFAULT '',
    municipio           TEXT DEFAULT '',
    uf                  TEXT DEFAULT '',
    token_focus         TEXT DEFAULT '',
    ambiente_focus      TEXT DEFAULT 'homologacao' CHECK(ambiente_focus IN ('homologacao','producao')),
    aliquota_icms       REAL DEFAULT 18,
    aliquota_pis        REAL DEFAULT 1.65,
    aliquota_cofins     REAL DEFAULT 7.6,
    aliquota_ipi        REAL DEFAULT 0,
    serie_nfe           INTEGER DEFAULT 1,
    proximo_numero_nfe  INTEGER DEFAULT 1,
    ativo               INTEGER NOT NULL DEFAULT 1,
    criado_em           TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS nfe_saida (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    numero          INTEGER NOT NULL,
    serie           INTEGER NOT NULL DEFAULT 1,
    chave           TEXT DEFAULT '',
    status          TEXT NOT NULL DEFAULT 'digitada'
                    CHECK(status IN ('digitada','autorizada','cancelada','denegada')),
    orcamento_id    INTEGER REFERENCES orcamentos(id),
    cliente_nome    TEXT NOT NULL,
    cliente_doc     TEXT DEFAULT '',
    valor           REAL NOT NULL,
    xml             TEXT DEFAULT '',
    protocolo       TEXT DEFAULT '',
    criado_em       TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS nfe_entrada (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    chave           TEXT NOT NULL UNIQUE,
    numero          INTEGER NOT NULL,
    serie           INTEGER NOT NULL DEFAULT 1,
    fornecedor_nome TEXT NOT NULL,
    fornecedor_doc  TEXT DEFAULT '',
    valor           REAL NOT NULL,
    data_emissao    TEXT NOT NULL,
    xml             TEXT DEFAULT '',
    criado_em       TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS ibpt (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    ncm             TEXT NOT NULL,
    descricao       TEXT DEFAULT '',
    aliquota_federal REAL DEFAULT 0,
    aliquota_estadual REAL DEFAULT 0,
    aliquota_municipal REAL DEFAULT 0,
    fonte           TEXT DEFAULT '',
    vigencia_inicio TEXT,
    vigencia_fim    TEXT,
    criado_em       TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_nfe_saida_status ON nfe_saida(status);
CREATE INDEX IF NOT EXISTS idx_ibpt_ncm ON ibpt(ncm);
"""


def guard(conn: sqlite3.Connection) -> bool:
    try:
        conn.execute("SELECT 1 FROM emitente LIMIT 1").fetchone()
    except sqlite3.OperationalError:
        return False
    return True


def forward(conn: sqlite3.Connection) -> None:
    conn.executescript(_SCHEMA)


def backward(conn: sqlite3.Connection) -> None:
    conn.executescript(
        "DROP TABLE IF EXISTS ibpt;"
        " DROP TABLE IF EXISTS nfe_entrada;"
        " DROP TABLE IF EXISTS nfe_saida;"
        " DROP TABLE IF EXISTS emitente;"
    )
