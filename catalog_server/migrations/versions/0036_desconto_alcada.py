"""0036 - Desconto por alçada no PDV (limite por usuário + autorização).

- `usuarios.desconto_limite_pct`      : % máxima de desconto que o usuário pode
  aplicar sem autorização (0 = não pode descontar).
- `usuarios.autoriza_desconto`        : permite ao usuário autorizar descontos
  acima do limite (gerente). Admin sempre autoriza.
- `orcamentos.usuario_id`             : usuário/vendedor que criou o orçamento.
- `orcamentos.desconto_autorizado`    : 1 quando o desconto acima da alçada foi
  aprovado (senha do gerente, na própria tela ou remoto).
- `orcamentos.desconto_autorizado_por`: usuário que autorizou.
- `orcamentos.desconto_autorizado_em` : quando a autorização ocorreu.
"""
from __future__ import annotations

import sqlite3

VERSION = 36
NAME = "Desconto por alçada no PDV (limite por usuário e autorização)"

_SQL = """
ALTER TABLE usuarios
    ADD COLUMN desconto_limite_pct REAL NOT NULL DEFAULT 0;

ALTER TABLE usuarios
    ADD COLUMN autoriza_desconto INTEGER NOT NULL DEFAULT 0;

ALTER TABLE orcamentos
    ADD COLUMN usuario_id INTEGER;

ALTER TABLE orcamentos
    ADD COLUMN desconto_autorizado INTEGER NOT NULL DEFAULT 0;

ALTER TABLE orcamentos
    ADD COLUMN desconto_autorizado_por INTEGER;

ALTER TABLE orcamentos
    ADD COLUMN desconto_autorizado_em TEXT;
"""


def guard(conn: sqlite3.Connection) -> bool:
    try:
        cols = {r[1] for r in conn.execute("PRAGMA table_info(usuarios)").fetchall()}
    except sqlite3.OperationalError:
        return False
    return "desconto_limite_pct" in cols


def forward(conn: sqlite3.Connection) -> None:
    conn.executescript(_SQL)


def backward(conn: sqlite3.Connection) -> None:
    for table in ("usuarios", "orcamentos"):
        cols = {
            "usuarios": ("desconto_limite_pct", "autoriza_desconto"),
            "orcamentos": ("usuario_id", "desconto_autorizado", "desconto_autorizado_por", "desconto_autorizado_em"),
        }[table]
        for col in cols:
            try:
                conn.execute(f"ALTER TABLE {table} DROP COLUMN {col}")
            except sqlite3.OperationalError:
                pass
