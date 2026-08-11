"""
0024 — Almoxarifado Avançado: localizações, tipos e expedição (Fase E).

- `depositos`: novos campos tipo e 8 localizações.
- `expedicao`: romaneio de expedição.
- `expedicao_itens`: itens do romaneio.
"""
from __future__ import annotations

import sqlite3

VERSION = 24
NAME = "Almoxarifado: localizações, tipos e expedição"

_COLUMNS: dict[str, dict[str, str]] = {
    "depositos": {
        "tipo": "TEXT DEFAULT 'proprio' CHECK(tipo IN ('proprio','terceiros','virtual'))",
        "localizacao_rua": "TEXT DEFAULT ''",
        "localizacao_prateleira": "TEXT DEFAULT ''",
        "localizacao_nivel": "TEXT DEFAULT ''",
        "localizacao_vão": "TEXT DEFAULT ''",
    },
}

_SCHEMA = """
CREATE TABLE IF NOT EXISTS expedicao (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    codigo          TEXT NOT NULL,
    deposito_id     INTEGER NOT NULL REFERENCES depositos(id),
    data_expedicao  TEXT NOT NULL DEFAULT (date('now')),
    status          TEXT NOT NULL DEFAULT 'pendente'
                    CHECK(status IN ('pendente','separando','conferido','carregado','finalizado')),
    transportadora  TEXT DEFAULT '',
    observacao      TEXT DEFAULT '',
    criado_em       TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS expedicao_itens (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    expedicao_id    INTEGER NOT NULL REFERENCES expedicao(id) ON DELETE CASCADE,
    orcamento_id    INTEGER REFERENCES orcamentos(id),
    variante_id     INTEGER NOT NULL REFERENCES variantes(id),
    quantidade      REAL NOT NULL,
    quantidade_sep  REAL DEFAULT 0,
    localizacao     TEXT DEFAULT '',
    criado_em       TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_exp_status ON expedicao(status);
CREATE INDEX IF NOT EXISTS idx_exp_dep ON expedicao(deposito_id);
"""


def guard(conn: sqlite3.Connection) -> bool:
    try:
        conn.execute("SELECT 1 FROM expedicao LIMIT 1").fetchone()
    except sqlite3.OperationalError:
        return False
    return True


def forward(conn: sqlite3.Connection) -> None:
    try:
        existing = {r[1] for r in conn.execute("PRAGMA table_info(depositos)").fetchall()}
    except sqlite3.OperationalError:
        existing = set()
    for col, ddl in _COLUMNS.get("depositos", {}).items():
        if col not in existing:
            conn.execute(f"ALTER TABLE depositos ADD COLUMN {col} {ddl}")
    conn.executescript(_SCHEMA)
    # Atualiza depósito Matriz para tipo proprio
    conn.execute("UPDATE depositos SET tipo='proprio' WHERE nome='Matriz' AND tipo IS NULL")


def backward(conn: sqlite3.Connection) -> None:
    conn.executescript(
        "DROP TABLE IF EXISTS expedicao_itens;"
        " DROP TABLE IF EXISTS expedicao;"
    )
