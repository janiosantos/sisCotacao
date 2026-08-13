"""0040 - Índice único de NCM no IBPT.

O repositório usa `ON CONFLICT(ncm)` no upsert, o que exige unicidade. O
`idx_ibpt_ncm` existente não é único.
"""
from __future__ import annotations

import sqlite3

VERSION = 40
NAME = "Índice único de NCM no IBPT"

_SQL = "CREATE UNIQUE INDEX IF NOT EXISTS idx_ibpt_ncm_uq ON ibpt(ncm);"


def guard(conn: sqlite3.Connection) -> bool:
    try:
        idx = {r[1] for r in conn.execute("PRAGMA index_list(ibpt)").fetchall()}
    except sqlite3.OperationalError:
        return False
    return "idx_ibpt_ncm_uq" in idx


def forward(conn: sqlite3.Connection) -> None:
    conn.execute(_SQL)


def backward(conn: sqlite3.Connection) -> None:
    conn.execute("DROP INDEX IF EXISTS idx_ibpt_ncm_uq")
