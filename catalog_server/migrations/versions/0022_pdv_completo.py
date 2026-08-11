"""
0022 — PDV Completo: workflow de status, totais, fretes e descontos (Fase C).

- `orcamentos`: novos campos para workflow (analise, liberado, faturado) + totais.
- `politica_descontos`: regras de desconto por perfil/faixa.
- `politica_fretes`: regras de frete por UF/valor.
"""
from __future__ import annotations

import sqlite3

VERSION = 22
NAME = "PDV completo: workflow, totais, fretes e descontos"

_COLUMNS: dict[str, dict[str, str]] = {
    "orcamentos": {
        "frete": "REAL DEFAULT 0",
        "seguro": "REAL DEFAULT 0",
        "despesas_acessorias": "REAL DEFAULT 0",
        "base_icms": "REAL DEFAULT 0",
        "valor_icms": "REAL DEFAULT 0",
        "base_ipi": "REAL DEFAULT 0",
        "valor_ipi": "REAL DEFAULT 0",
        "base_pis_cofins": "REAL DEFAULT 0",
        "valor_pis": "REAL DEFAULT 0",
        "valor_cofins": "REAL DEFAULT 0",
        "total_liquido": "REAL DEFAULT 0",
    },
}

_SCHEMA = """
CREATE TABLE IF NOT EXISTS politica_descontos (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    nome            TEXT NOT NULL,
    tipo            TEXT NOT NULL DEFAULT 'percentual' CHECK(tipo IN ('percentual','valor_fixo')),
    valor_maximo    REAL NOT NULL DEFAULT 0,
    valor_minimo    REAL NOT NULL DEFAULT 0,
    perfil          TEXT DEFAULT '',
    ativo           INTEGER NOT NULL DEFAULT 1,
    criado_em       TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS politica_fretes (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    nome            TEXT NOT NULL,
    uf              TEXT NOT NULL DEFAULT '',
    valor_minimo_pedido REAL DEFAULT 0,
    valor_frete     REAL NOT NULL DEFAULT 0,
    tipo            TEXT NOT NULL DEFAULT 'fixo' CHECK(tipo IN ('fixo','percentual','por_kg')),
    ativo           INTEGER NOT NULL DEFAULT 1,
    criado_em       TEXT NOT NULL DEFAULT (datetime('now'))
);
"""


def guard(conn: sqlite3.Connection) -> bool:
    try:
        conn.execute("SELECT 1 FROM politica_descontos LIMIT 1").fetchone()
    except sqlite3.OperationalError:
        return False
    return True


def forward(conn: sqlite3.Connection) -> None:
    # Colunas novas em orcamentos
    try:
        existing = {r[1] for r in conn.execute("PRAGMA table_info(orcamentos)").fetchall()}
    except sqlite3.OperationalError:
        existing = set()
    for col, ddl in _COLUMNS.get("orcamentos", {}).items():
        if col not in existing:
            conn.execute(f"ALTER TABLE orcamentos ADD COLUMN {col} {ddl}")

    conn.executescript(_SCHEMA)

    # Políticas padrão
    if not conn.execute("SELECT 1 FROM politica_descontos LIMIT 1").fetchone():
        conn.executemany(
            "INSERT INTO politica_descontos (nome, tipo, valor_maximo, perfil) VALUES (?,?,?,?)",
            [("Desconto padrão vendedor", "percentual", 5, "vendedor"),
             ("Desconto padrão admin", "percentual", 15, "admin"),
             ("Desconto valor fixo até R$ 50", "valor_fixo", 50, "")],
        )
    if not conn.execute("SELECT 1 FROM politica_fretes LIMIT 1").fetchone():
        conn.executemany(
            "INSERT INTO politica_fretes (nome, uf, valor_minimo_pedido, valor_frete, tipo) VALUES (?,?,?,?,?)",
            [("Frete SP capital", "SP", 200, 15, "fixo"),
             ("Frete SP interior", "SP", 300, 25, "fixo"),
             ("Frete RJ", "RJ", 300, 35, "fixo"),
             ("Frete MG", "MG", 300, 30, "fixo"),
             ("Frete Sul (PR/SC/RS)", "", 500, 45, "fixo"),
             ("Frete gratuito (acima R$ 500)", "", 500, 0, "fixo")],
        )


def backward(conn: sqlite3.Connection) -> None:
    conn.executescript(
        "DROP TABLE IF EXISTS politica_fretes;"
        " DROP TABLE IF EXISTS politica_descontos;"
    )
