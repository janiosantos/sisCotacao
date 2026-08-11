"""
0026 — Estoque mínimo/máximo e alertas de ruptura.
"""
from __future__ import annotations
import sqlite3

VERSION = 26
NAME = "Estoque mínimo/máximo e alertas"

def guard(conn: sqlite3.Connection) -> bool:
    try:
        cols = {r[1] for r in conn.execute("PRAGMA table_info(estoque_saldo)").fetchall()}
        return "estoque_minimo" in cols
    except sqlite3.OperationalError:
        return False

def forward(conn: sqlite3.Connection) -> None:
    try:
        cols = {r[1] for r in conn.execute("PRAGMA table_info(estoque_saldo)").fetchall()}
    except sqlite3.OperationalError:
        cols = set()
    if "estoque_minimo" not in cols:
        conn.execute("ALTER TABLE estoque_saldo ADD COLUMN estoque_minimo REAL DEFAULT 0")
    if "estoque_maximo" not in cols:
        conn.execute("ALTER TABLE estoque_saldo ADD COLUMN estoque_maximo REAL DEFAULT 0")

def backward(conn: sqlite3.Connection) -> None:
    pass
