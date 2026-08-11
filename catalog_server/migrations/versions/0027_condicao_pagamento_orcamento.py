"""
0027 — Condição de pagamento nos orçamentos.
"""
from __future__ import annotations
import sqlite3

VERSION = 27
NAME = "Condição de pagamento nos orçamentos"

def guard(conn: sqlite3.Connection) -> bool:
    try:
        cols = {r[1] for r in conn.execute("PRAGMA table_info(orcamentos)").fetchall()}
        return "condicao_pagamento_id" in cols
    except sqlite3.OperationalError:
        return False

def forward(conn: sqlite3.Connection) -> None:
    try:
        cols = {r[1] for r in conn.execute("PRAGMA table_info(orcamentos)").fetchall()}
    except sqlite3.OperationalError:
        cols = set()
    if "condicao_pagamento_id" not in cols:
        conn.execute("ALTER TABLE orcamentos ADD COLUMN condicao_pagamento_id INTEGER REFERENCES condicoes_pagamento(id)")

def backward(conn: sqlite3.Connection) -> None:
    pass
