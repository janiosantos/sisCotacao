"""0046 - Vínculo do cliente à venda (destinatário fiscal).

`orcamentos` passa a guardar:
- `cliente_id`   : cliente cadastrado vinculado à venda (destinatário da nota).
- `cliente_doc`  : CPF/CNPJ do destinatário no momento da venda.
- contexto do destino já existente (uf_destino, tipo_cliente, contribuinte, ie)
  passa a ser preenchido automaticamente a partir do cliente vinculado.
"""
from __future__ import annotations

import sqlite3


def _cols(conn: sqlite3.Connection, table: str) -> set[str]:
    return {r[1] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()}


_COLS = (
    "cliente_id INTEGER",
    "cliente_doc TEXT",
    "ie TEXT",
)


def guard(conn: sqlite3.Connection) -> bool:
    try:
        return "cliente_id" in _cols(conn, "orcamentos")
    except sqlite3.OperationalError:
        return False


def forward(conn: sqlite3.Connection) -> None:
    for col in _COLS:
        if col.split()[0] not in _cols(conn, "orcamentos"):
            conn.execute(f"ALTER TABLE orcamentos ADD COLUMN {col}")


def backward(conn: sqlite3.Connection) -> None:
    for col in _COLS:
        name = col.split()[0]
        try:
            conn.execute(f"ALTER TABLE orcamentos DROP COLUMN {name}")
        except sqlite3.OperationalError:
            pass
