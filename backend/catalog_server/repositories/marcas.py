"""Repositório de marcas (tabela `marcas` criada na migração 0053).

A marca continua sendo informada em texto livre no cadastro, mas o sistema
mantém uma tabela normalizada (`marcas`) que recebe create-or-get de cada nome
e vincula `produtos_cadastro.marca_id`. Assim a interface pode oferecer um
autocomplete das marcas já conhecidas e a consulta fica estável por id.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from catalog_server.pgsql import PgConnection as _Conn


def listar(conn: _Conn, somente_ativas: bool = False) -> list[dict]:
    sql = "SELECT * FROM marcas"
    if somente_ativas:
        sql += " WHERE ativo=1"
    sql += " ORDER BY nome"
    return [dict(r) for r in conn.execute(sql).fetchall()]


def resolver(conn: _Conn, nome: str) -> int | None:
    """Devolve o id da marca, criando-a se o nome ainda não existir (create-or-get)."""
    nome = (nome or "").strip()
    if not nome:
        return None
    row = conn.execute(
        "SELECT id FROM marcas"
        " WHERE f_unaccent(LOWER(nome))=f_unaccent(LOWER(?))",
        (nome,),
    ).fetchone()
    if row is not None:
        return row["id"]
    return conn.execute(
        "INSERT INTO marcas (nome, ativo) VALUES (?, 1)", (nome,)
    ).lastrowid


def atualizar_codigo(conn: _Conn, marca_id: int, codigo: str) -> bool:
    codigo = (codigo or "").strip().upper()
    codigo = codigo or None
    cur = conn.execute(
        "UPDATE marcas SET codigo=? WHERE id=?", (codigo, marca_id)
    )
    return cur.rowcount > 0


def criar(conn: _Conn, nome: str) -> dict:
    """Cria (ou devolve) uma marca pelo nome, com `ativo`."""
    mid = resolver(conn, nome)
    row = conn.execute("SELECT * FROM marcas WHERE id=?", (mid,)).fetchone()
    return dict(row)
