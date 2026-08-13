"""0047 - Código IBGE dos municípios (emitente e cliente).

`emitente.c_municipio` e `clientes.c_municipio` guardam o código IBGE do
município, usado no `cMun`/`cMunFG` da NF-e/NFC-e.
"""
from __future__ import annotations

import sqlite3


def _cols(conn: sqlite3.Connection, table: str) -> set[str]:
    return {r[1] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()}


def guard(conn: sqlite3.Connection) -> bool:
    try:
        return "c_municipio" in _cols(conn, "emitente")
    except sqlite3.OperationalError:
        return False


def forward(conn: sqlite3.Connection) -> None:
    for table in ("emitente", "clientes"):
        if "c_municipio" not in _cols(conn, table):
            conn.execute(f"ALTER TABLE {table} ADD COLUMN c_municipio TEXT")


def backward(conn: sqlite3.Connection) -> None:
    for table in ("emitente", "clientes"):
        try:
            conn.execute(f"ALTER TABLE {table} DROP COLUMN c_municipio")
        except sqlite3.OperationalError:
            pass
