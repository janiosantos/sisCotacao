"""
0052 — Bandeira e código de autorização no caixa (recebimento via cartão).

Recebimentos com cartão (débito/crédito) precisam registrar a bandeira e o
código de autorização da operadora — hoje o caixa só guarda a forma de
pagamento.
"""
from __future__ import annotations

import sqlite3

VERSION = 52
NAME = "Bandeira e código de autorização em caixa_movimento (cartão)"

_COLUNAS = {
    "bandeira": "TEXT",
    "codigo_autorizacao": "TEXT",
}


def guard(conn: sqlite3.Connection) -> bool:
    cols = {r[1] for r in conn.execute("PRAGMA table_info(caixa_movimento)").fetchall()}
    return "bandeira" in cols and "codigo_autorizacao" in cols


def forward(conn: sqlite3.Connection) -> None:
    existing = {r[1] for r in conn.execute("PRAGMA table_info(caixa_movimento)").fetchall()}
    for col, ddl in _COLUNAS.items():
        if col not in existing:
            conn.execute(f"ALTER TABLE caixa_movimento ADD COLUMN {col} {ddl}")


def backward(conn: sqlite3.Connection) -> None:
    # SQLite não remove colunas de forma trivial; nada a fazer no downgrade.
    pass
