"""0034 - Unidades de compra predefinidas (unidades_compra).

Cria a tabela `unidades_compra` com as unidades comerciais que passam a ser
as únicas opções do campo `unidade_compra` em `fornecedor_variantes` (antes
texto livre). A tabela ganha um seed com as unidades mais comuns do comércio;
o CRUD fica disponível em Cadastros > Unidades.
"""
from __future__ import annotations

import sqlite3

VERSION = 34
NAME = "Tabela de unidades de compra predefinidas"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS unidades_compra (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    sigla         TEXT NOT NULL UNIQUE,
    descricao     TEXT NOT NULL DEFAULT '',
    ativo         INTEGER NOT NULL DEFAULT 1,
    criado_em     TEXT NOT NULL DEFAULT (datetime('now'))
);
"""

SEED = [
    ("CX", "Caixa"),
    ("UN", "Unidade"),
    ("PCT", "Pacote"),
    ("PC", "Peça"),
    ("RL", "Rolo"),
    ("MT", "Metro"),
    ("M2", "Metro quadrado"),
    ("KG", "Quilograma"),
    ("LT", "Litro"),
    ("PAR", "Par"),
    ("DZ", "Dúzia"),
    ("FD", "Fardo"),
    ("CN", "Cento"),
]


def guard(conn: sqlite3.Connection) -> bool:
    try:
        conn.execute("SELECT 1 FROM unidades_compra LIMIT 1").fetchone()
    except sqlite3.OperationalError:
        return False
    return True


def forward(conn: sqlite3.Connection) -> None:
    conn.executescript(_SCHEMA)
    for sigla, descricao in SEED:
        conn.execute(
            "INSERT OR IGNORE INTO unidades_compra (sigla, descricao, ativo) VALUES (?,?,1)",
            (sigla, descricao),
        )


def backward(conn: sqlite3.Connection) -> None:
    conn.execute("DROP TABLE IF EXISTS unidades_compra")