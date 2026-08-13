"""0043 - Cadastro fiscal: cliente (contribuinte/IE) e emitente (CRT, IBS/CBS).

- `clientes.contribuinte`  : 'contribuinte' | 'nao_contribuinte' | '' (não definido).
- `clientes.ie`            : inscrição estadual (quando aplicável).
- `emitente.crt`           : CRT (1=Simples, 2=Simples excesso de sublimite, 3=Regime Normal).
- `emitente.aliquota_ibs/cbs` + vigências: parâmetros da transição da Reforma
  Tributária (NECESSITA VALIDAÇÃO — editáveis sem alterar código).
"""
from __future__ import annotations

import sqlite3

VERSION = 43
NAME = "Cadastro fiscal: cliente contribuinte/IE e emitente CRT/IBS-CBS"

_COLS_CLIENTES = (
    "contribuinte TEXT DEFAULT ''",
    "ie TEXT DEFAULT ''",
)
_COLS_EMITENTE = (
    "crt INTEGER DEFAULT 1",
    "aliquota_ibs REAL DEFAULT 0",
    "aliquota_cbs REAL DEFAULT 0",
    "ibs_vigencia_inicio TEXT",
    "ibs_vigencia_fim TEXT",
    "cbs_vigencia_inicio TEXT",
    "cbs_vigencia_fim TEXT",
)


def _cols(conn: sqlite3.Connection, table: str) -> set[str]:
    return {r[1] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()}


def guard(conn: sqlite3.Connection) -> bool:
    try:
        return "contribuinte" in _cols(conn, "clientes")
    except sqlite3.OperationalError:
        return False


def forward(conn: sqlite3.Connection) -> None:
    for col in _COLS_CLIENTES:
        if col.split()[0] not in _cols(conn, "clientes"):
            conn.execute(f"ALTER TABLE clientes ADD COLUMN {col}")
    for col in _COLS_EMITENTE:
        if col.split()[0] not in _cols(conn, "emitente"):
            conn.execute(f"ALTER TABLE emitente ADD COLUMN {col}")


def backward(conn: sqlite3.Connection) -> None:
    for table, cols in (("clientes", _COLS_CLIENTES), ("emitente", _COLS_EMITENTE)):
        for col in cols:
            name = col.split()[0]
            try:
                conn.execute(f"ALTER TABLE {table} DROP COLUMN {name}")
            except sqlite3.OperationalError:
                pass
