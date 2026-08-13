"""0048 - Loja de material: unidades, localização, inventário, devoluções e config.

Evolui o cadastro de produto-filho (variante) e o estoque para loja física de
material de construção (balcão + depósito), sem duplicar o que já existe
(famílias/atributos = variações; unidades_compra = unidades).

- `variantes`: peso, dimensões, unidade de venda, embalagem (unid. por caixa) e
  fator de conversão (ex.: caixa = X m²) e localização padrão.
- `estoque_saldo.localizacao`: endereçamento físico (Corredor/Prateleira/Box).
- `config_loja`: configurações chave/valor (ex.: bloquear_venda_sem_estoque).
- `inventarios`/`inventario_itens`: contagem física com divergência e ajuste.
- `devolucoes`: devolução/troca de itens vendidos.
"""
from __future__ import annotations

import sqlite3

VERSION = 48
NAME = "Loja de material: unidades, localização, inventário, devoluções e config"

_COLS_VARIANTES = (
    "peso REAL DEFAULT 0",
    "dimensoes TEXT DEFAULT ''",
    "unidade_venda TEXT DEFAULT 'UN'",
    "embalagem REAL DEFAULT 1",
    "fator_conversao REAL DEFAULT 1",
    "localizacao TEXT DEFAULT ''",
)
_COLS_ESTOQUE = ("localizacao TEXT DEFAULT ''",)

_SQL = """
CREATE TABLE IF NOT EXISTS config_loja (
    chave       TEXT PRIMARY KEY,
    valor       TEXT DEFAULT '',
    atualizado_em TEXT
);

CREATE TABLE IF NOT EXISTS inventarios (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    nome        TEXT NOT NULL,
    deposito_id INTEGER REFERENCES depositos(id),
    data        TEXT NOT NULL DEFAULT (date('now')),
    status      TEXT NOT NULL DEFAULT 'aberto'
                CHECK(status IN ('aberto','finalizado')),
    criado_em   TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS inventario_itens (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    inventario_id       INTEGER NOT NULL REFERENCES inventarios(id) ON DELETE CASCADE,
    variante_id         INTEGER NOT NULL REFERENCES variantes(id),
    deposito_id         INTEGER NOT NULL REFERENCES depositos(id),
    quantidade_sistema  REAL NOT NULL DEFAULT 0,
    quantidade_contada  REAL,
    divergencia         REAL,
    localizacao         TEXT DEFAULT '',
    criado_em           TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(inventario_id, variante_id, deposito_id)
);

CREATE TABLE IF NOT EXISTS devolucoes (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    orcamento_id INTEGER REFERENCES orcamentos(id),
    variante_id  INTEGER REFERENCES variantes(id),
    quantidade   REAL NOT NULL DEFAULT 1,
    motivo       TEXT DEFAULT '',
    tipo         TEXT NOT NULL DEFAULT 'devolucao'
                 CHECK(tipo IN ('devolucao','troca')),
    status       TEXT NOT NULL DEFAULT 'registrada'
                 CHECK(status IN ('registrada','estornada','trocada')),
    deposito_id  INTEGER NOT NULL DEFAULT 1,
    usuario_id   INTEGER REFERENCES usuarios(id),
    criado_em    TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_inv_itens_inv ON inventario_itens(inventario_id);
CREATE INDEX IF NOT EXISTS idx_dev_orcamento ON devolucoes(orcamento_id);
"""


def _cols(conn: sqlite3.Connection, table: str) -> set[str]:
    return {r[1] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()}


def guard(conn: sqlite3.Connection) -> bool:
    try:
        return "peso" in _cols(conn, "variantes")
    except sqlite3.OperationalError:
        return False


def forward(conn: sqlite3.Connection) -> None:
    for col in _COLS_VARIANTES:
        if col.split()[0] not in _cols(conn, "variantes"):
            conn.execute(f"ALTER TABLE variantes ADD COLUMN {col}")
    for col in _COLS_ESTOQUE:
        if col.split()[0] not in _cols(conn, "estoque_saldo"):
            conn.execute(f"ALTER TABLE estoque_saldo ADD COLUMN {col}")
    conn.executescript(_SQL)


def backward(conn: sqlite3.Connection) -> None:
    conn.executescript(
        "DROP TABLE IF EXISTS devolucoes;"
        " DROP TABLE IF EXISTS inventario_itens;"
        " DROP TABLE IF EXISTS inventarios;"
        " DROP TABLE IF EXISTS config_loja;"
    )
    for table, cols in (("variantes", _COLS_VARIANTES), ("estoque_saldo", _COLS_ESTOQUE)):
        for col in cols:
            try:
                conn.execute(f"ALTER TABLE {table} DROP COLUMN {col.split()[0]}")
            except sqlite3.OperationalError:
                pass
