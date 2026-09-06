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

_NAO_INFORMADO = object()


def _clean(value: str) -> str:
    return (value or "").strip()


def _subgrupo_existe(conn: _Conn, subgrupo_id: int | None) -> bool:
    if subgrupo_id is None:
        return True
    return conn.execute(
        "SELECT 1 FROM subgrupos WHERE id=?", (subgrupo_id,)
    ).fetchone() is not None


def resolve_categoria(
    conn: _Conn, categoria: str, subgrupo_id: int | None = None
) -> int | None:
    """Devolve o id de uma categoria, criando-a se o nome ainda não existir."""
    nome = _clean(categoria)
    if not nome:
        return None
    row = conn.execute(
        "SELECT id, subgrupo_id FROM categorias"
        " WHERE f_unaccent(LOWER(nome))=f_unaccent(LOWER(?))",
        (nome,),
    ).fetchone()
    if row is not None:
        atual = row["subgrupo_id"]
        if subgrupo_id is not None and atual is not None and int(atual) != subgrupo_id:
            raise ValueError("categoria ja vinculada a outro subgrupo")
        if subgrupo_id is not None and atual is None:
            if not _subgrupo_existe(conn, subgrupo_id):
                raise ValueError("subgrupo nao encontrado")
            conflito = conn.execute(
                "SELECT 1 FROM produtos_cadastro WHERE categoria_id=?"
                " AND subgrupo_id IS NOT NULL AND subgrupo_id<>? LIMIT 1",
                (row["id"], subgrupo_id),
            ).fetchone()
            if conflito:
                raise ValueError(
                    "categoria possui produtos em outro subgrupo; ajuste-a na tela de categorias"
                )
            conn.execute(
                "UPDATE categorias SET subgrupo_id=? WHERE id=?",
                (subgrupo_id, row["id"]),
            )
        return row["id"]
    if not _subgrupo_existe(conn, subgrupo_id):
        raise ValueError("subgrupo nao encontrado")
    return conn.execute(
        "INSERT INTO categorias (nome, ativo, subgrupo_id) VALUES (?, 1, ?)",
        (nome, subgrupo_id),
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
        "SELECT id FROM subcategorias WHERE categoria_id=?"
        " AND f_unaccent(LOWER(nome))=f_unaccent(LOWER(?))",
        (categoria_id, nome),
    ).fetchone()
    if row is not None:
        return row["id"]
    return conn.execute(
        "INSERT INTO subcategorias (categoria_id, nome, ativo) VALUES (?, ?, 1)",
        (categoria_id, nome),
    ).lastrowid


def resolve(
    conn: _Conn,
    categoria: str,
    subcategoria: str,
    subgrupo_id: int | None = None,
) -> tuple[int | None, int | None]:
    """Resolve ambos os nomes para ids (create-or-get)."""
    categoria_id = resolve_categoria(conn, categoria, subgrupo_id)
    subcategoria_id = resolve_subcategoria(conn, categoria_id, subcategoria)
    return categoria_id, subcategoria_id


def validar_hierarquia(
    conn: _Conn,
    grupo_id: int | None,
    subgrupo_id: int | None,
    categoria_id: int | None,
    subcategoria_id: int | None,
) -> tuple[int | None, int | None, int | None, int | None]:
    """Valida e completa a cadeia Grupo -> Subgrupo -> Categoria -> Subcategoria."""
    if subcategoria_id is not None:
        sub = conn.execute(
            "SELECT categoria_id FROM subcategorias WHERE id=?", (subcategoria_id,)
        ).fetchone()
        if not sub:
            raise ValueError("subcategoria nao encontrada")
        if categoria_id is not None and int(sub["categoria_id"]) != categoria_id:
            raise ValueError("subcategoria nao pertence a categoria selecionada")
        categoria_id = int(sub["categoria_id"])

    if categoria_id is not None:
        cat = conn.execute(
            "SELECT subgrupo_id FROM categorias WHERE id=?", (categoria_id,)
        ).fetchone()
        if not cat:
            raise ValueError("categoria nao encontrada")
        if cat["subgrupo_id"] is not None:
            cat_subgrupo_id = int(cat["subgrupo_id"])
            if subgrupo_id is not None and subgrupo_id != cat_subgrupo_id:
                raise ValueError("categoria nao pertence ao subgrupo selecionado")
            subgrupo_id = cat_subgrupo_id

    if subgrupo_id is not None:
        subgrupo = conn.execute(
            "SELECT grupo_id FROM subgrupos WHERE id=?", (subgrupo_id,)
        ).fetchone()
        if not subgrupo:
            raise ValueError("subgrupo nao encontrado")
        subgrupo_grupo_id = int(subgrupo["grupo_id"])
        if grupo_id is not None and grupo_id != subgrupo_grupo_id:
            raise ValueError("subgrupo nao pertence ao grupo selecionado")
        grupo_id = subgrupo_grupo_id

    if grupo_id is not None and conn.execute(
        "SELECT 1 FROM grupos WHERE id=?", (grupo_id,)
    ).fetchone() is None:
        raise ValueError("grupo nao encontrado")

    if categoria_id is None:
        subcategoria_id = None
    return grupo_id, subgrupo_id, categoria_id, subcategoria_id


# ---- CRUD ----

def listar() -> list[dict]:
    """Retorna todas as categorias com suas subcategorias e contagem de produtos."""
    with system_conn() as conn:
        rows = conn.execute(
            """
            SELECT c.id, c.nome, c.ativo, c.subgrupo_id,
                   sg.nome AS subgrupo_nome, sg.codigo AS subgrupo_codigo,
                   g.id AS grupo_id, g.nome AS grupo_nome, g.codigo AS grupo_codigo,
                   sc.id AS subcategoria_id, sc.nome AS subcategoria_nome,
                   sc.ativo AS subcategoria_ativo,
                   COUNT(p.id) AS product_count,
                   SUM(CASE WHEN p.ativo=1 THEN 1 ELSE 0 END) AS active_product_count
              FROM categorias c
              LEFT JOIN subgrupos sg ON sg.id=c.subgrupo_id
              LEFT JOIN grupos g ON g.id=sg.grupo_id
              LEFT JOIN subcategorias sc ON sc.categoria_id=c.id
              LEFT JOIN produtos_cadastro p ON p.subcategoria_id=sc.id
             GROUP BY c.id, c.nome, c.ativo, c.subgrupo_id,
                      sg.nome, sg.codigo, g.id, g.nome, g.codigo,
                      sc.id, sc.nome, sc.ativo
             ORDER BY c.nome COLLATE NOCASE, sc.nome COLLATE NOCASE
            """
        ).fetchall()
        por_categoria: dict[int, dict] = {}
        for row in rows:
            categoria_id = int(row["id"])
            item = por_categoria.setdefault(
                categoria_id,
                {
                    "id": categoria_id,
                    "nome": row["nome"],
                    "ativo": bool(row["ativo"]),
                    "subgrupo_id": row["subgrupo_id"],
                    "subgrupo_nome": row["subgrupo_nome"],
                    "subgrupo_codigo": row["subgrupo_codigo"],
                    "grupo_id": row["grupo_id"],
                    "grupo_nome": row["grupo_nome"],
                    "grupo_codigo": row["grupo_codigo"],
                    "subcategorias": [],
                },
            )
            if row["subcategoria_id"] is not None:
                item["subcategorias"].append(
                    {
                        "id": int(row["subcategoria_id"]),
                        "nome": row["subcategoria_nome"],
                        "ativo": bool(row["subcategoria_ativo"]),
                        "product_count": int(row["product_count"] or 0),
                        "active_product_count": int(row["active_product_count"] or 0),
                    }
                )
        return list(por_categoria.values())


def criar_categoria(nome: str, subgrupo_id: int | None = None) -> int | None:
    with system_conn() as conn:
        return resolve_categoria(conn, nome, subgrupo_id)


def atualizar_categoria(
    categoria_id: int,
    nome: str,
    subgrupo_id: int | None | object = _NAO_INFORMADO,
) -> bool:
    with system_conn() as conn:
        if subgrupo_id is _NAO_INFORMADO:
            cur = conn.execute(
                "UPDATE categorias SET nome=? WHERE id=?",
                (nome.strip(), categoria_id),
            )
            return cur.rowcount > 0
        if not _subgrupo_existe(conn, subgrupo_id):
            raise ValueError("subgrupo nao encontrado")
        cur = conn.execute(
            "UPDATE categorias SET nome=?, subgrupo_id=? WHERE id=?",
            (nome.strip(), subgrupo_id, categoria_id),
        )
        if cur.rowcount > 0 and subgrupo_id is not None:
            grupo = conn.execute(
                "SELECT grupo_id FROM subgrupos WHERE id=?", (subgrupo_id,)
            ).fetchone()
            conn.execute(
                "UPDATE produtos_cadastro SET grupo_id=?, subgrupo_id=?, atualizado_em=NOW()"
                " WHERE categoria_id=?",
                (grupo["grupo_id"], subgrupo_id, categoria_id),
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
            "SELECT COUNT(*) FROM produtos_cadastro WHERE subcategoria_id=?",
            (subcategoria_id,),
        ).fetchone()[0]
        rows = conn.execute(
            "SELECT p.id, p.nome, p.marca, p.external_id, p.familia_id,"
            " p.status_cadastro, p.ativo,"
            " CASE WHEN p.preco > 0 THEN p.preco END AS price_min"
            " FROM produtos_cadastro p WHERE p.subcategoria_id=?"
            " ORDER BY p.nome COLLATE NOCASE LIMIT ? OFFSET ?",
            (subcategoria_id, limit, offset),
        ).fetchall()
        return [dict(r) for r in rows], total


def reclassificar_produtos(
    produto_ids: list[int], categoria: str, subcategoria: str
) -> int:
    """Move produtos para outra categoria/subcategoria. Retorna qtde afetada."""
    with system_conn() as conn:
        if not categoria:
            raise ValueError("informe a categoria de destino")
        cat_id = resolve_categoria(conn, categoria)
        sub_id = resolve_subcategoria(conn, cat_id, subcategoria) if categoria else None
        hierarquia = conn.execute(
            "SELECT c.subgrupo_id, sg.grupo_id FROM categorias c"
            " LEFT JOIN subgrupos sg ON sg.id=c.subgrupo_id WHERE c.id=?",
            (cat_id,),
        ).fetchone()
        count = 0
        for pid in produto_ids:
            if hierarquia and hierarquia["subgrupo_id"] is not None:
                cur = conn.execute(
                    "UPDATE produtos_cadastro SET grupo_id=?, subgrupo_id=?,"
                    " categoria_id=?, subcategoria_id=?, atualizado_em=NOW() WHERE id=?",
                    (hierarquia["grupo_id"], hierarquia["subgrupo_id"], cat_id, sub_id, pid),
                )
            else:
                cur = conn.execute(
                    "UPDATE produtos_cadastro SET categoria_id=?, subcategoria_id=?,"
                    " atualizado_em=NOW() WHERE id=?",
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
