"""Resolução de categoria/subcategoria por nome para os ids normalizados.

A taxonomia agora vive em tabelas próprias (`categorias`/`subcategorias`) e
`produtos_cadastro` guarda apenas `categoria_id`/`subcategoria_id`. Como a API
e vários fluxos ainda informam os nomes em texto livre (CRUD manual, scrap,
importação por URL), este módulo resolve create-or-get de cada nome para o id
correspondente.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from catalog_server.db import system_conn

if TYPE_CHECKING:
    from catalog_server.pgsql import PgConnection as _Conn


def _clean(value: str) -> str:
    return (value or "").strip()


def resolve_categoria(conn: _Conn, categoria: str) -> int | None:
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
    conn: _Conn, categoria_id: int | None, subcategoria: str
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
    conn: _Conn, categoria: str, subcategoria: str
) -> tuple[int | None, int | None]:
    """Resolve ambos os nomes para ids (create-or-get)."""
    categoria_id = resolve_categoria(conn, categoria)
    subcategoria_id = resolve_subcategoria(conn, categoria_id, subcategoria)
    return categoria_id, subcategoria_id


# ---- CRUD ----

def listar() -> list[dict]:
    """Retorna todas as categorias com suas subcategorias e contagem de produtos."""
    with system_conn() as conn:
        cats = conn.execute("SELECT id, nome, ativo FROM categorias ORDER BY nome").fetchall()
        result = []
        for c in cats:
            cid = int(c["id"])
            subs = conn.execute(
                "SELECT id, nome, ativo FROM subcategorias WHERE categoria_id=? ORDER BY nome",
                (cid,),
            ).fetchall()
            subs_list = []
            for s in subs:
                cnt = conn.execute(
                    "SELECT COUNT(*) FROM produtos_cadastro WHERE subcategoria_id=? AND ativo=1",
                    (int(s["id"]),),
                ).fetchone()[0]
                item = dict(s)
                item["product_count"] = cnt
                subs_list.append(item)
            result.append({
                "id": c["id"],
                "nome": c["nome"],
                "ativo": bool(c["ativo"]),
                "subcategorias": subs_list,
            })
        return result


def criar_categoria(nome: str) -> int | None:
    with system_conn() as conn:
        return resolve_categoria(conn, nome)


def atualizar_categoria(categoria_id: int, nome: str) -> bool:
    with system_conn() as conn:
        cur = conn.execute(
            "UPDATE categorias SET nome=? WHERE id=?", (nome.strip(), categoria_id),
        )
        return cur.rowcount > 0


def excluir_categoria(categoria_id: int) -> tuple[bool, str]:
    with system_conn() as conn:
        filhos = conn.execute(
            "SELECT COUNT(*) FROM subcategorias WHERE categoria_id=?", (categoria_id,)
        ).fetchone()[0]
        if filhos > 0:
            return False, f"Exclua as subcategorias primeiro ({filhos} vinculadas)"
        prods = conn.execute(
            "SELECT COUNT(*) FROM produtos_cadastro WHERE categoria_id=?", (categoria_id,)
        ).fetchone()[0]
        if prods > 0:
            return False, f"{prods} produtos vinculados a esta categoria"
        cur = conn.execute("DELETE FROM categorias WHERE id=?", (categoria_id,))
        return cur.rowcount > 0, ""


def criar_subcategoria(categoria_id: int, nome: str) -> int | None:
    with system_conn() as conn:
        return resolve_subcategoria(conn, categoria_id, nome)


def atualizar_subcategoria(subcategoria_id: int, nome: str) -> bool:
    with system_conn() as conn:
        cur = conn.execute(
            "UPDATE subcategorias SET nome=? WHERE id=?", (nome.strip(), subcategoria_id),
        )
        return cur.rowcount > 0


def produtos_por_subcategoria(subcategoria_id: int, offset: int = 0, limit: int = 60) -> tuple[list[dict], int]:
    """Retorna produtos de uma subcategoria com paginação."""
    with system_conn() as conn:
        total = conn.execute(
            "SELECT COUNT(*) FROM produtos_cadastro WHERE subcategoria_id=? AND ativo=1",
            (subcategoria_id,),
        ).fetchone()[0]
        rows = conn.execute(
            "SELECT p.id, p.nome, p.marca, p.external_id, p.familia_id,"
            " (SELECT MIN(preco) FROM variantes v WHERE v.produto_id=p.id AND v.ativo=1 AND preco>0) AS price_min"
            " FROM produtos_cadastro p WHERE p.subcategoria_id=? AND p.ativo=1"
            " ORDER BY p.nome COLLATE NOCASE LIMIT ? OFFSET ?",
            (subcategoria_id, limit, offset),
        ).fetchall()
        return [dict(r) for r in rows], total


def reclassificar_produtos(
    produto_ids: list[int], categoria: str, subcategoria: str
) -> int:
    """Move produtos para outra categoria/subcategoria. Retorna qtde afetada."""
    with system_conn() as conn:
        cat_id = resolve_categoria(conn, categoria)
        sub_id = resolve_subcategoria(conn, cat_id, subcategoria) if categoria else None
        count = 0
        for pid in produto_ids:
            cur = conn.execute(
                "UPDATE produtos_cadastro SET categoria_id=?, subcategoria_id=?,"
                " atualizado_em=datetime('now') WHERE id=? AND ativo=1",
                (cat_id, sub_id, pid),
            )
            if cur.rowcount:
                count += 1
        return count


def excluir_subcategoria(subcategoria_id: int) -> tuple[bool, str]:
    with system_conn() as conn:
        prods = conn.execute(
            "SELECT COUNT(*) FROM produtos_cadastro WHERE subcategoria_id=?",
            (subcategoria_id,),
        ).fetchone()[0]
        if prods > 0:
            return False, f"{prods} produtos vinculados a esta subcategoria"
        cur = conn.execute("DELETE FROM subcategorias WHERE id=?", (subcategoria_id,))
        return cur.rowcount > 0, ""