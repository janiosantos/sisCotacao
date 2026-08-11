"""0009 — Dissolve familias-fake: produtos sem atributos viram simples.

Familias sem nenhum `familia_atributos` definido nao sao familias de verdade
— sao apenas rotulos de navegacao. Produtos nessas familias ganham
`familia_id=NULL` (produto simples, sem variacoes).
Eles continuam navegaveis via `categoria_id`/`subcategoria_id` que ja possuem.
"""
from __future__ import annotations
import sqlite3

VERSION = 9
NAME = "Dissolver familias-fake (produtos simples sem atributos)"


def guard(conn: sqlite3.Connection) -> bool:
    qtd = conn.execute(
        "SELECT COUNT(*) FROM produtos_cadastro p "
        "JOIN familias f ON f.id=p.familia_id "
        "LEFT JOIN familia_atributos fa ON fa.familia_id=f.id "
        "WHERE fa.id IS NULL AND p.ativo=1"
    ).fetchone()
    return qtd[0] == 0


def forward(conn: sqlite3.Connection) -> None:
    fake_ids = [
        r[0] for r in conn.execute(
            "SELECT f.id FROM familias f "
            "LEFT JOIN familia_atributos fa ON fa.familia_id=f.id "
            "WHERE fa.id IS NULL "
            "AND EXISTS (SELECT 1 FROM produtos_cadastro WHERE familia_id=f.id AND ativo=1)"
        ).fetchall()
    ]

    if not fake_ids:
        return

    placeholders = ",".join("?" * len(fake_ids))
    conn.execute("BEGIN")
    try:
        conn.execute(
            f"UPDATE produtos_cadastro SET familia_id=NULL, atualizado_em=datetime('now') "
            f"WHERE familia_id IN ({placeholders}) AND ativo=1",
            fake_ids,
        )
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise


def backward(conn: sqlite3.Connection) -> None:
    pass
