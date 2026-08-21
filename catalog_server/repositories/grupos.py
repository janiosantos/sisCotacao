"""Repositório de grupos e subgrupos (taxonomia de SKU estruturado).

`grupos` (codigo, nome) e `subgrupos` (grupo_id, codigo, nome) alimentam os
dois primeiros segmentos do SKU `[GRUPO]-[SUBGRUPO]-[MARCA]-[ATRIBUTOS]`.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from catalog_server.pgsql import PgConnection as _Conn


def listar_grupos(conn: _Conn, somente_ativos: bool = False) -> list[dict]:
    sql = "SELECT * FROM grupos"
    if somente_ativos:
        sql += " WHERE ativo=1"
    sql += " ORDER BY codigo"
    return [dict(r) for r in conn.execute(sql).fetchall()]


def criar_grupo(conn: _Conn, codigo: str, nome: str, ativo: int = 1) -> dict:
    codigo = (codigo or "").strip().upper()
    nome = (nome or "").strip()
    cur = conn.execute(
        "INSERT INTO grupos (codigo, nome, ativo) VALUES (?, ?, ?)"
        " ON CONFLICT (codigo) DO UPDATE SET nome=EXCLUDED.nome, ativo=EXCLUDED.ativo"
        " RETURNING id",
        (codigo, nome, ativo),
    )
    gid = cur.fetchone()["id"]
    return dict(conn.execute("SELECT * FROM grupos WHERE id=?", (gid,)).fetchone())


def atualizar_grupo(conn: _Conn, grupo_id: int, codigo: str, nome: str, ativo: int = 1) -> bool:
    codigo = (codigo or "").strip().upper()
    nome = (nome or "").strip()
    cur = conn.execute(
        "UPDATE grupos SET codigo=?, nome=?, ativo=? WHERE id=?",
        (codigo, nome, ativo, grupo_id),
    )
    return cur.rowcount > 0


def excluir_grupo(conn: _Conn, grupo_id: int) -> tuple[bool, str]:
    filhos = conn.execute(
        "SELECT COUNT(*) FROM subgrupos WHERE grupo_id=?", (grupo_id,)
    ).fetchone()[0]
    if filhos > 0:
        return False, f"Exclua os subgrupos primeiro ({filhos} vinculados)"
    prods = conn.execute(
        "SELECT COUNT(*) FROM produtos_cadastro WHERE grupo_id=?", (grupo_id,)
    ).fetchone()[0]
    if prods > 0:
        return False, f"{prods} produtos vinculados a este grupo"
    cur = conn.execute("DELETE FROM grupos WHERE id=?", (grupo_id,))
    return cur.rowcount > 0, ""


def listar_subgrupos(conn: _Conn, grupo_id: int, somente_ativos: bool = False) -> list[dict]:
    sql = "SELECT * FROM subgrupos WHERE grupo_id=?"
    if somente_ativos:
        sql += " AND ativo=1"
    sql += " ORDER BY codigo"
    return [dict(r) for r in conn.execute(sql, (grupo_id,)).fetchall()]


def criar_subgrupo(conn: _Conn, grupo_id: int, codigo: str, nome: str, ativo: int = 1) -> dict:
    codigo = (codigo or "").strip().upper()
    nome = (nome or "").strip()
    cur = conn.execute(
        "INSERT INTO subgrupos (grupo_id, codigo, nome, ativo) VALUES (?, ?, ?, ?)"
        " ON CONFLICT (grupo_id, codigo) DO UPDATE SET nome=EXCLUDED.nome, ativo=EXCLUDED.ativo"
        " RETURNING id",
        (grupo_id, codigo, nome, ativo),
    )
    sid = cur.fetchone()["id"]
    return dict(conn.execute("SELECT * FROM subgrupos WHERE id=?", (sid,)).fetchone())


def atualizar_subgrupo(conn: _Conn, subgrupo_id: int, codigo: str, nome: str, ativo: int = 1) -> bool:
    codigo = (codigo or "").strip().upper()
    nome = (nome or "").strip()
    cur = conn.execute(
        "UPDATE subgrupos SET codigo=?, nome=?, ativo=? WHERE id=?",
        (codigo, nome, ativo, subgrupo_id),
    )
    return cur.rowcount > 0


def excluir_subgrupo(conn: _Conn, subgrupo_id: int) -> tuple[bool, str]:
    prods = conn.execute(
        "SELECT COUNT(*) FROM produtos_cadastro WHERE subgrupo_id=?", (subgrupo_id,)
    ).fetchone()[0]
    if prods > 0:
        return False, f"{prods} produtos vinculados a este subgrupo"
    cur = conn.execute("DELETE FROM subgrupos WHERE id=?", (subgrupo_id,))
    return cur.rowcount > 0, ""
