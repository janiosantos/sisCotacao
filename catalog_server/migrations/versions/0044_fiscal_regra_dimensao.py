"""0044 - Dimensão da regra fiscal (composição operação × produto).

Resolve a limitação do modelo de regra única: uma regra de PRODUTO (ex.: ICMS-ST
por NCM/CEST) agora pode COMPOR com uma regra de OPERAÇÃO (CFOP/CST por UF,
cliente, natureza) em vez de uma anular a outra.

- `operacao`: critérios de contexto (UF, cliente, natureza, finalidade, modelo).
- `produto`:  critérios do produto (NCM/CEST/origem) — ex.: atributos de ST.
- `geral`:    compatibilidade (regras antigas sem dimensão).

O motor resolve uma regra por dimensão e combina os resultados.
"""
from __future__ import annotations

import sqlite3


def _cols(conn: sqlite3.Connection, table: str) -> set[str]:
    return {r[1] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()}


def guard(conn: sqlite3.Connection) -> bool:
    try:
        return "dimensao" in _cols(conn, "fiscal_regra")
    except sqlite3.OperationalError:
        return False


def forward(conn: sqlite3.Connection) -> None:
    if "dimensao" not in _cols(conn, "fiscal_regra"):
        conn.execute("ALTER TABLE fiscal_regra ADD COLUMN dimensao TEXT NOT NULL DEFAULT 'geral'")


def backward(conn: sqlite3.Connection) -> None:
    try:
        conn.execute("ALTER TABLE fiscal_regra DROP COLUMN dimensao")
    except sqlite3.OperationalError:
        pass
