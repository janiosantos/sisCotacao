"""Resolução de categoria/subcategoria por nome para os ids normalizados.

A taxonomia agora vive em tabelas próprias (`categorias`/`subcategorias`) e
`produtos_cadastro` guarda apenas `categoria_id`/`subcategoria_id`. Como a API
e vários fluxos ainda informam os nomes em texto livre (CRUD manual, scrap,
importação por URL), este módulo resolve create-or-get de cada nome para o id
correspondente.
"""
from __future__ import annotations

import sqlite3


def _clean(value: str) -> str:
    return (value or "").strip()


def resolve_categoria(conn: sqlite3.Connection, categoria: str) -> int | None:
    """Devolve o id de uma categoria, criando-a se o nome ainda não existir."""
    nome = _clean(categoria)
    if not nome:
        return None
    row = conn.execute("SELECT id FROM categorias WHERE nome=?", (nome,)).fetchone()
    if row is not None:
        return row["id"]
    return conn.execute(
        "INSERT INTO categorias (nome, ativo) VALUES (?, 1)", (nome,)
    ).lastrowid


def resolve_subcategoria(
    conn: sqlite3.Connection, categoria_id: int | None, subcategoria: str
) -> int | None:
    """Devolve o id de uma subcategoria dentro da categoria, criando se necessário.

    A unicidade é por par (categoria_id, nome), então o mesmo texto em
    categorias diferentes vira registros distintos.
    """
    nome = _clean(subcategoria)
    if not categoria_id or not nome:
        return None
    row = conn.execute(
        "SELECT id FROM subcategorias WHERE categoria_id=? AND nome=?",
        (categoria_id, nome),
    ).fetchone()
    if row is not None:
        return row["id"]
    return conn.execute(
        "INSERT INTO subcategorias (categoria_id, nome, ativo) VALUES (?, ?, 1)",
        (categoria_id, nome),
    ).lastrowid


def resolve(
    conn: sqlite3.Connection, categoria: str, subcategoria: str
) -> tuple[int | None, int | None]:
    """Resolve ambos os nomes para ids (create-or-get)."""
    categoria_id = resolve_categoria(conn, categoria)
    subcategoria_id = resolve_subcategoria(conn, categoria_id, subcategoria)
    return categoria_id, subcategoria_id