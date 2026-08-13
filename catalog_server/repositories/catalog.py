"""RepositÃ³rio do catÃ¡logo â€” lÃª da base Ãºnica (`server.db`).

O catÃ¡logo agora consome o mesmo cadastro de produtos (`produtos_cadastro` +
`variantes`) alimentado pelo scraper e pelo CRUD manual. Cada
`produtos_cadastro` corresponde a um card; suas variantes ativas sÃ£o as
variaÃ§Ãµes (cor/bitola/potÃªnciaâ€¦) exibidas no seletor.
"""
from __future__ import annotations

import re

from catalog_server import fts
from catalog_server.db import system_conn
from catalog_server.grouping import PACKAGE_LABELS
from catalog_server.utils import image_url

# CÃ³digo de barras/cÃ³digo interno: curto, sem espaÃ§os e com dÃ­gitos.
_CODE_RE = re.compile(r"^[A-Za-z0-9./-]{1,16}$")


def _is_code_query(q: str) -> bool:
    """Verdadeiro quando a busca parece um cÃ³digo (SKU/EAN) e nÃ£o um nome."""
    return bool(q) and any(c.isdigit() for c in q) and bool(_CODE_RE.fullmatch(q))


def _order_abc(ordenar: str = "", prefix: str = "", extra: str = "") -> str:
    """ClÃ¡usula ORDER BY do catÃ¡logo; `ordenar="abc"` prioriza a Curva ABC (Aâ†’C)."""
    if ordenar == "abc":
        base = (
            "CASE WHEN p.classe_abc IN ('A','B','C') THEN p.classe_abc ELSE 'Z' END,"
            " p.ordem_abc, p.nome COLLATE NOCASE"
        )
        if extra:
            base += ", " + extra
        return "ORDER BY " + base
    if prefix:
        return "ORDER BY " + prefix + ", p.nome COLLATE NOCASE" + (", " + extra if extra else "")
    if extra:
        return "ORDER BY p.nome COLLATE NOCASE, " + extra
    return "ORDER BY p.nome COLLATE NOCASE, p.id"


class CatalogRepository:

# ------------------------------------------------------------------

    def list_products(
        self,
        categoria: str = "",
        subcategoria: str = "",
        q: str = "",
        classe: str = "",
        em_linha: bool = True,
        offset: int = 0,
        limit: int = 60,
        agrupado: bool = True,
        ordenar: str = "",
) -> tuple[list[dict], int]:
        """Retorna os itens do catÃ¡logo.

        `agrupado=True`: um card por produtos_cadastro, com as variaÃ§Ãµes
        (cor/diÃ¢metro) agrupadas num seletor â€” ideal para montar a RFQ ao
        fornecedor. `agrupado=False`: cada variante Ã© um item individual com
        seu prÃ³prio preÃ§o â€” ideal para o orÃ§amento ao cliente.
        `classe`: filtro pela Curva ABC (A/B/C); usado para priorizar a RFQ.
        `em_linha`: se True (padrÃ£o), exibe sÃ³ o rolar em foco (exclui
        equipamentos de alto valor marcados `em_linha=0`).
        `ordenar`: "abc" ordena por Curva ABC (Aâ†’C por `ordem_abc`); vazio
        mantÃ©m a ordenaÃ§Ã£o padrÃ£o (nome/relevÃ¢ncia).
        """
        q = (q or "").strip()
        ordenar = (ordenar or "").strip().lower()
        with system_conn() as conn:
            fts.ensure_fts(conn)
            if agrupado:
                if q and not fts.is_empty(conn) and not _is_code_query(q):
                    rows, total = self._search_fts(conn, categoria, subcategoria, q, classe, em_linha, offset, limit, ordenar)
                else:
                    rows, total = self._browse(conn, categoria, subcategoria, q, classe, em_linha, offset, limit, ordenar)
                produto_ids = [r["id"] for r in rows]
                variants = self._load_variants(conn, produto_ids)
                variante_ids = [v["id"] for v in variants]
                attrs = self._load_variant_attrs(conn, variante_ids)
                images = self._load_images(conn, produto_ids)
                attr_defs = self._load_attr_defs(conn, [r["familia_id"] for r in rows])
                suppliers = self._load_variant_suppliers(conn, variante_ids)

            cards = []
            if agrupado:
                for r in rows:
                    card = self._build_card(r, variants, attrs, images, attr_defs, suppliers)
                    if card:
                        cards.append(card)
            else:
                if q and not fts.is_empty(conn) and not _is_code_query(q):
                    rows, total = self._search_flat(conn, categoria, subcategoria, q, classe, em_linha, offset, limit, ordenar)
                else:
                    rows, total = self._browse_flat(conn, categoria, subcategoria, q, classe, em_linha, offset, limit, ordenar)
                variant_ids = [r["id"] for r in rows]
                attrs = self._load_variant_attrs(conn, variant_ids)
                images = self._load_images(conn, [r["produto_id"] for r in rows])
                attr_defs = self._load_attr_defs(conn, [r["familia_id"] for r in rows])
                suppliers = self._load_variant_suppliers(conn, variant_ids)
                cards = [self._flat_card(r, attrs, images, attr_defs, suppliers) for r in rows]
        return cards, total

    def _browse(
        self, conn, categoria: str, subcategoria: str, q: str, classe: str, em_linha: bool, offset: int, limit: int, ordenar: str = ""
    ) -> tuple[list[dict], int]:
        joins = (
            " LEFT JOIN categorias cat ON cat.id=p.categoria_id"
            " LEFT JOIN subcategorias sub ON sub.id=p.subcategoria_id"
        )
        where = [
            "p.ativo=1",
            "EXISTS (SELECT 1 FROM variantes v WHERE v.produto_id=p.id AND v.ativo=1)",
        ]
        params: list = []
        if categoria:
            where.append("cat.nome=?")
            params.append(categoria)
        if subcategoria:
            where.append("sub.nome=?")
            params.append(subcategoria)
        if classe:
            where.append("p.classe_abc=?")
            params.append(classe)
        if em_linha:
            where.append("p.em_linha=1")
        if q:
            like = f"%{q}%"
            where.append(
                "(p.nome LIKE ? OR p.marca LIKE ? OR EXISTS ("
                " SELECT 1 FROM variantes v2 WHERE v2.produto_id=p.id"
                " AND (v2.sku LIKE ? OR v2.ean LIKE ?)))"
            )
            params += [like, like, like, like]
        where_sql = " AND ".join(where)

        total = conn.execute(
            f"SELECT COUNT(*) AS n FROM produtos_cadastro p{joins} WHERE {where_sql}",
            params,
        ).fetchone()["n"]
        rows = conn.execute(
            f"""
                SELECT p.id, p.familia_id, p.nome, p.marca,
                       COALESCE(cat.nome, '') AS categoria,
                       COALESCE(sub.nome, '') AS subcategoria,
                       p.embalagem, p.classe_abc, p.ordem_abc
                FROM produtos_cadastro p{joins}
                WHERE {where_sql}
                {_order_abc(ordenar)}
                LIMIT ? OFFSET ?
                """,
            params + [limit, offset],
        ).fetchall()
        return [dict(r) for r in rows], total

    def _search_fts(
        self, conn, categoria: str, subcategoria: str, q: str, classe: str, em_linha: bool, offset: int, limit: int, ordenar: str = ""
    ) -> tuple[list[dict], int]:
        match = fts.search_query(q)
        if not match:
            return [], 0
        joins = (
            " LEFT JOIN categorias cat ON cat.id=p.categoria_id"
            " LEFT JOIN subcategorias sub ON sub.id=p.subcategoria_id"
        )
        where = [
            "p.ativo=1",
            "EXISTS (SELECT 1 FROM variantes v WHERE v.produto_id=p.id AND v.ativo=1)",
            "produtos_fts MATCH ?",
        ]
        params: list = [match]
        if categoria:
            where.append("cat.nome=?")
            params.append(categoria)
        if subcategoria:
            where.append("sub.nome=?")
            params.append(subcategoria)
        if classe:
            where.append("p.classe_abc=?")
            params.append(classe)
        if em_linha:
            where.append("p.em_linha=1")
        where_sql = " AND ".join(where)

        total = conn.execute(
            f"SELECT COUNT(*) AS c FROM produtos_fts ft JOIN produtos_cadastro p ON p.id=ft.produto_id{joins} WHERE {where_sql}",
            params,
        ).fetchone()["c"]
        rows = conn.execute(
            f"""
            SELECT p.id, p.familia_id, p.nome, p.marca,
                   COALESCE(cat.nome, '') AS categoria,
                   COALESCE(sub.nome, '') AS subcategoria, p.embalagem, p.classe_abc, p.ordem_abc
            FROM produtos_fts ft
            JOIN produtos_cadastro p ON p.id=ft.produto_id{joins}
            WHERE {where_sql}
            {_order_abc(ordenar, prefix="bm25(produtos_fts)")}
            LIMIT ? OFFSET ?
            """,
params + [limit, offset],
        ).fetchall()
        return [dict(r) for r in rows], total

    # ------------------------------------------------------------------
    # Modo "listar variantes" (orÃ§amento ao cliente) â€” cada variante Ã© um item
    # individual com seu prÃ³prio preÃ§o; paginaÃ§Ã£o no nÃ­vel da variante.
    # ------------------------------------------------------------------

    def _browse_flat(
        self, conn, categoria: str, subcategoria: str, q: str, classe: str, em_linha: bool, offset: int, limit: int, ordenar: str = ""
    ) -> tuple[list[dict], int]:
        joins = (
            " LEFT JOIN categorias cat ON cat.id=p.categoria_id"
            " LEFT JOIN subcategorias sub ON sub.id=p.subcategoria_id"
        )
        where = ["v.ativo=1", "p.ativo=1"]
        params: list = []
        if categoria:
            where.append("cat.nome=?")
            params.append(categoria)
        if subcategoria:
            where.append("sub.nome=?")
            params.append(subcategoria)
        if classe:
            where.append("p.classe_abc=?")
            params.append(classe)
        if em_linha:
            where.append("p.em_linha=1")
        if q:
            like = f"%{q}%"
            where.append("(p.nome LIKE ? OR p.marca LIKE ? OR v.sku LIKE ? OR v.ean LIKE ?)")
            params += [like, like, like, like]
        where_sql = " AND ".join(where)
        join = (
            " FROM variantes v JOIN produtos_cadastro p ON p.id=v.produto_id"
            f"{joins}"
        )

        total = conn.execute(
            f"SELECT COUNT(*) AS n{join} WHERE {where_sql}", params
        ).fetchone()["n"]
        rows = conn.execute(
            f"""
            SELECT v.id, v.produto_id, v.sku, v.ean, v.preco, v.old_price,
                   v.pix_price, v.installment, v.marca AS marca_var,
                   p.nome, p.marca AS marca_prod, p.familia_id,
                   COALESCE(cat.nome, '') AS categoria,
                   COALESCE(sub.nome, '') AS subcategoria, p.embalagem,
                   p.classe_abc, p.ordem_abc,
                   v.unidade_venda, v.embalagem AS embalagem_qtd, v.ncm
            {join}
            WHERE {where_sql}
            {_order_abc(ordenar, extra="p.id, v.id")}
            LIMIT ? OFFSET ?
            """,
            params + [limit, offset],
        ).fetchall()
        return [dict(r) for r in rows], total

    def _search_flat(
        self, conn, categoria: str, subcategoria: str, q: str, classe: str, em_linha: bool, offset: int, limit: int, ordenar: str = ""
    ) -> tuple[list[dict], int]:
        match = fts.search_query(q)
        if not match:
            return [], 0
        joins = (
            " LEFT JOIN categorias cat ON cat.id=p.categoria_id"
            " LEFT JOIN subcategorias sub ON sub.id=p.subcategoria_id"
        )
        where = [
            "v.ativo=1",
            "p.ativo=1",
            "p.id IN (SELECT ft.produto_id FROM produtos_fts ft WHERE produtos_fts MATCH ?)",
        ]
        params: list = [match]
        if categoria:
            where.append("cat.nome=?")
            params.append(categoria)
        if subcategoria:
            where.append("sub.nome=?")
            params.append(subcategoria)
        if classe:
            where.append("p.classe_abc=?")
            params.append(classe)
        if em_linha:
            where.append("p.em_linha=1")
        where_sql = " AND ".join(where)
        join = (
            " FROM variantes v JOIN produtos_cadastro p ON p.id=v.produto_id"
            f"{joins}"
        )

        total = conn.execute(
            f"SELECT COUNT(*) AS n{join} WHERE {where_sql}", params
        ).fetchone()["n"]
        rows = conn.execute(
            f"""
            SELECT v.id, v.produto_id, v.sku, v.ean, v.preco, v.old_price,
                   v.pix_price, v.installment, v.marca AS marca_var,
                   p.nome, p.marca AS marca_prod, p.familia_id,
                   COALESCE(cat.nome, '') AS categoria,
                   COALESCE(sub.nome, '') AS subcategoria, p.embalagem,
                   p.classe_abc, p.ordem_abc,
                   v.unidade_venda, v.embalagem AS embalagem_qtd, v.ncm
            {join}
            WHERE {where_sql}
            {_order_abc(ordenar, extra="p.id, v.id")}
            LIMIT ? OFFSET ?
            """,
            params + [limit, offset],
        ).fetchall()
        return [dict(r) for r in rows], total

    # ------------------------------------------------------------------
    # OrdenaÃ§Ã£o
    # ------------------------------------------------------------------

    def categorias(self) -> dict[str, list[str]]:
        """Ãrvore categoria -> subcategorias, a partir da taxonomia normalizada.

        SÃ³ categorias com ao menos um produto ativo (em linha) aparecem, para o
        filtro do catÃ¡logo nÃ£o oferecer opÃ§Ãµes vazias.
        """
        with system_conn() as conn:
            pairs = conn.execute(
                """
                SELECT DISTINCT p.categoria_id, p.subcategoria_id
                FROM produtos_cadastro p
                JOIN variantes v ON v.produto_id = p.id AND v.ativo = 1
                WHERE p.ativo = 1 AND p.categoria_id IS NOT NULL
                """
            ).fetchall()
            cat_ids = {r["categoria_id"] for r in pairs}
            sub_ids = {r["subcategoria_id"] for r in pairs if r["subcategoria_id"] is not None}
            cats: dict[int, str] = {}
            if cat_ids:
                ph = ",".join("?" * len(cat_ids))
                cats = {
                    r["id"]: r["nome"]
                    for r in conn.execute(
                        f"SELECT id, nome FROM categorias WHERE id IN ({ph})", tuple(cat_ids)
                    ).fetchall()
                }
            subs: dict[int, tuple[str, int]] = {}
            if sub_ids:
                ph = ",".join("?" * len(sub_ids))
                subs = {
                    r["id"]: (r["nome"], r["categoria_id"])
                    for r in conn.execute(
                        f"SELECT id, nome, categoria_id FROM subcategorias WHERE id IN ({ph})",
                        tuple(sub_ids),
                    ).fetchall()
                }
        tree: dict[str, list[str]] = {}
        for r in pairs:
            nome_cat = cats.get(r["categoria_id"])
            if not nome_cat:
                continue
            sub_nome = None
            if r["subcategoria_id"] is not None:
                sub = subs.get(r["subcategoria_id"])
                if not sub or sub[1] != r["categoria_id"]:
                    continue
                sub_nome = sub[0]
            if sub_nome not in tree.setdefault(nome_cat, []):
                if sub_nome:
                    tree[nome_cat].append(sub_nome)
        return tree

    # ------------------------------------------------------------------

    def resumo_abc(
        self, categoria: str = "", subcategoria: str = "", q: str = "", em_linha: bool = True
    ) -> dict:
        """Contagem de produtos por classe ABC sob os mesmos filtros do catÃ¡logo."""
        q = (q or "").strip()
        joins = (
            " LEFT JOIN categorias cat ON cat.id=p.categoria_id"
            " LEFT JOIN subcategorias sub ON sub.id=p.subcategoria_id"
        )
        where = [
            "p.ativo=1",
            "EXISTS (SELECT 1 FROM variantes v WHERE v.produto_id=p.id AND v.ativo=1)",
        ]
        params: list = []
        if categoria:
            where.append("cat.nome=?")
            params.append(categoria)
        if subcategoria:
            where.append("sub.nome=?")
            params.append(subcategoria)
        if em_linha:
            where.append("p.em_linha=1")
        if q:
            like = f"%{q}%"
            where.append(
                "(p.nome LIKE ? OR p.marca LIKE ? OR EXISTS ("
                " SELECT 1 FROM variantes v2 WHERE v2.produto_id=p.id"
                " AND (v2.sku LIKE ? OR v2.ean LIKE ?)))"
            )
            params += [like, like, like, like]
        with system_conn() as conn:
            rows = conn.execute(
                f"SELECT p.classe_abc AS c, COUNT(*) AS n FROM produtos_cadastro p{joins}"
                f" WHERE {' AND '.join(where)} GROUP BY p.classe_abc",
                params,
            ).fetchall()
        out = {"A": 0, "B": 0, "C": 0, "sem": 0}
        for r in rows:
            out[r["c"] if r["c"] in ("A", "B", "C") else "sem"] = r["n"]
        return out

# ------------------------------------------------------------------

    def product(self, product_id: int) -> dict | None:
        """Detalhe de uma variante (id = variante)."""
        with system_conn() as conn:
            row = conn.execute(
                """
                SELECT v.*, p.nome, p.marca AS produto_marca,
                       cat.nome AS categoria, sub.nome AS subcategoria
                FROM variantes v
                JOIN produtos_cadastro p ON p.id=v.produto_id
                LEFT JOIN categorias cat ON cat.id=p.categoria_id
                LEFT JOIN subcategorias sub ON sub.id=p.subcategoria_id
                WHERE v.id=? AND v.ativo=1 AND p.ativo=1
                """,
                (product_id,),
            ).fetchone()
            if row is None:
                return None
            images = conn.execute(
                """
                SELECT filename FROM imagens_produto
                WHERE produto_id=? AND (variante_id=? OR variante_id IS NULL)
                ORDER BY (variante_id IS NULL), ordem, id
                """,
                (row["produto_id"], product_id),
            ).fetchall()
            color = ""
            color_row = conn.execute(
                """
                SELECT va.valor FROM variante_atributos va
                JOIN familia_atributos fa ON fa.id=va.atributo_id
                WHERE va.variante_id=? AND LOWER(fa.nome) LIKE '%cor%'
                LIMIT 1
                """,
                (product_id,),
            ).fetchone()
            if color_row:
                color = color_row["valor"]

        return {
            "id": row["id"],
            "sku": row["sku"] or "",
            "ean": row["ean"] or "",
            "name": row["nome"] or "",
            "brand": row["marca"] or row["produto_marca"] or "",
            "color": color,
            "price": row["preco"] or 0,
            "old_price": row["old_price"],
            "pix_price": row["pix_price"] or 0,
            "installment": row["installment"] or "",
            "category": row["categoria"] or "",
            "subcategory": row["subcategoria"] or "",
            "image_urls": [u for u in (image_url(i["filename"]) for i in images) if u],
        }

    # ------------------------------------------------------------------

    def products_by_ids(self, ids: list[int]) -> dict[int, dict]:
        """Resolve ids de variante para enriquecer cotaÃ§Ãµes/histÃ³rico."""
        if not ids:
            return {}
        out: dict[int, dict] = {}
        with system_conn() as conn:
            for chunk_start in range(0, len(ids), 500):
                chunk = ids[chunk_start : chunk_start + 500]
                placeholders = ",".join("?" * len(chunk))
                rows = conn.execute(
                    f"""
SELECT v.id, v.sku, v.preco, v.marca, v.external_id,
                           p.nome, p.marca AS produto_marca,
                           cat.nome AS categoria, sub.nome AS subcategoria,
                           (SELECT im.filename FROM imagens_produto im
                            WHERE (im.variante_id=v.id OR (im.variante_id IS NULL AND im.produto_id=p.id))
                            ORDER BY (im.variante_id IS NULL), im.ordem, im.id LIMIT 1) AS imagem_filename
                    FROM variantes v
                    JOIN produtos_cadastro p ON p.id=v.produto_id
                    LEFT JOIN categorias cat ON cat.id=p.categoria_id
                    LEFT JOIN subcategorias sub ON sub.id=p.subcategoria_id
                    WHERE v.id IN ({placeholders})
                    """,
                    chunk,
                ).fetchall()
                for r in rows:
                    out[r["id"]] = {
                        "id": r["id"],
                        "sku": r["sku"] or "",
                        "name": r["nome"] or "",
                        "brand": r["marca"] or r["produto_marca"] or "",
                        "category": r["categoria"] or "",
                        "subcategory": r["subcategoria"] or "",
                        "imagem_url": image_url(r["imagem_filename"]),
                        "price": r["preco"] or 0,
                    }
        return out

    # ------------------------------------------------------------------

    def products_with_history(self) -> list[dict]:
        """Variantes disponÃ­veis para consulta de histÃ³rico."""
        with system_conn() as conn:
            rows = conn.execute(
                """
                SELECT v.id, v.sku, p.nome
                FROM variantes v
                JOIN produtos_cadastro p ON p.id=v.produto_id
                WHERE v.ativo=1 AND p.ativo=1
                ORDER BY p.nome COLLATE NOCASE
                """
            ).fetchall()
        return [
            {"id": r["id"], "sku": r["sku"] or "", "name": r["nome"] or ""} for r in rows
        ]

    # ------------------------------------------------------------------
    # Carga em lote
    # ------------------------------------------------------------------

    @staticmethod
    def _load_variants(conn, produto_ids: list[int]) -> list[dict]:
        if not produto_ids:
            return []
        placeholders = ",".join("?" * len(produto_ids))
        return [
            dict(r)
            for r in conn.execute(
                f"""
                SELECT v.id, v.produto_id, v.sku, v.ean, v.preco, v.old_price,
                       v.pix_price, v.installment, v.marca
                FROM variantes v
                WHERE v.produto_id IN ({placeholders}) AND v.ativo=1
                ORDER BY v.id
                """,
                produto_ids,
            ).fetchall()
        ]

    @staticmethod
    def _load_variant_attrs(conn, variante_ids: list[int]) -> dict[int, dict]:
        out: dict[int, dict] = {}
        if not variante_ids:
            return out
        placeholders = ",".join("?" * len(variante_ids))
        rows = conn.execute(
            f"""
            SELECT va.variante_id, fa.id AS atributo_id, fa.nome, va.valor
            FROM variante_atributos va
            JOIN familia_atributos fa ON fa.id=va.atributo_id
            WHERE va.variante_id IN ({placeholders})
            """,
            variante_ids,
        ).fetchall()
        for r in rows:
            out.setdefault(r["variante_id"], {})[r["atributo_id"]] = r["valor"]
        return out

    @staticmethod
    def _load_variant_suppliers(conn, variante_ids: list[int]) -> dict[int, list[str]]:
        """Nome dos fornecedores mapeados para cada variante (cÃ³digos de compra)."""
        out: dict[int, list[str]] = {}
        if not variante_ids:
            return out
        placeholders = ",".join("?" * len(variante_ids))
        rows = conn.execute(
            f"""
            SELECT fv.variante_id, s.nome
            FROM fornecedor_variantes fv
            JOIN fornecedores s ON s.id=fv.fornecedor_id
            WHERE fv.variante_id IN ({placeholders})
            ORDER BY s.nome
            """,
            variante_ids,
        ).fetchall()
        for r in rows:
            out.setdefault(r["variante_id"], []).append(r["nome"])
        return out

    @staticmethod
    def _load_images(conn, produto_ids: list[int]) -> dict[int, list[str]]:
        out: dict[int, list[str]] = {}
        if not produto_ids:
            return out
        placeholders = ",".join("?" * len(produto_ids))
        rows = conn.execute(
            f"""
            SELECT produto_id, variante_id, filename
            FROM imagens_produto
            WHERE produto_id IN ({placeholders})
            ORDER BY ordem, id
            """,
            produto_ids,
        ).fetchall()
        for r in rows:
            out.setdefault(r["produto_id"], []).append(r["filename"])
        return out

    @staticmethod
    def _load_attr_defs(conn, familia_ids: list[int]) -> dict[int, list[dict]]:
        out: dict[int, list[dict]] = {}
        if not familia_ids:
            return out
        placeholders = ",".join("?" * len(familia_ids))
        rows = conn.execute(
            f"""
            SELECT id, familia_id, nome
            FROM familia_atributos
            WHERE familia_id IN ({placeholders})
            ORDER BY ordem, id
            """,
            familia_ids,
        ).fetchall()
        for r in rows:
            out.setdefault(r["familia_id"], []).append(
                {"id": r["id"], "label": r["nome"]}
            )
        return out

    # ------------------------------------------------------------------
    # Montagem dos cards
    # ------------------------------------------------------------------

    def _build_card(
        self,
        produto: dict,
        variants: list[dict],
        attrs: dict[int, dict],
        images: dict[int, list[str]],
        attr_defs: dict[int, list[dict]],
        suppliers: dict[int, list[str]] | None = None,
    ) -> dict | None:
        pid = produto["id"]
        vs = [v for v in variants if v["produto_id"] == pid]
        if not vs:
            return None
        base = produto["nome"] or ""
        package = produto["embalagem"] or None
        category = produto["categoria"] or ""
        subcategory = produto["subcategoria"] or ""

        def first_image() -> str | None:
            fns = images.get(pid, [])
            return image_url(fns[0]) if fns else None

        if len(vs) == 1:
            v = vs[0]
            vattrs = attrs.get(v["id"], {})
            return {
                "group": False,
                "id": v["id"],
                "sku": v["sku"] or "",
                "ean": v["ean"] or "",
                "name": base,
                "base": base,
                "package": package,
                "package_label": PACKAGE_LABELS.get(package, ""),
                "attrs": vattrs,
                "brand": v["marca"] or produto["marca"] or "",
                "price": v["preco"] or 0,
                "old_price": v["old_price"],
                "pix_price": v["pix_price"] or 0,
                "installment": v["installment"] or "",
                "category": category,
                "subcategory": subcategory,
                "classe_abc": produto.get("classe_abc") or "",
                "imagem_url": first_image(),
                "fornecedores": (suppliers or {}).get(v["id"], []),
            }

        defs = attr_defs.get(produto["familia_id"], [])
        attr_ids = [d["id"] for d in defs]
        options: dict[int, list[str]] = {aid: [] for aid in attr_ids}
        seen_options: dict[int, set] = {aid: set() for aid in attr_ids}
        for v in vs:
            vattrs = attrs.get(v["id"], {})
            for aid in attr_ids:
                val = vattrs.get(aid)
                if val and val not in seen_options[aid]:
                    seen_options[aid].add(val)
                    options[aid].append(val)
        attr_cards = []
        for d in defs:
            opts = options[d["id"]]
            some_missing = any(attrs.get(v["id"], {}).get(d["id"]) is None for v in vs)
            if len(opts) >= 2 or (len(opts) == 1 and some_missing):
                attr_cards.append({"id": d["id"], "label": d["label"], "options": opts})
        brands = sorted(
            {v["marca"] or produto["marca"] or "" for v in vs if (v["marca"] or produto["marca"])}
        )
        prices = [v["preco"] or 0 for v in vs]

        variants_out = []
        for v in vs:
            vattrs = attrs.get(v["id"], {})
            variants_out.append(
                {
                    "id": v["id"],
                    "sku": v["sku"] or "",
                    "name": base,
                    "brand": v["marca"] or produto["marca"] or "",
                    "attrs": vattrs,
                    "price": v["preco"] or 0,
                    "imagem_url": first_image(),
                    "fornecedores": (suppliers or {}).get(v["id"], []),
                }
            )

        return {
            "group": True,
            "id": pid,
            "sku": variants_out[0]["sku"],
            "name": base,
            "base": base,
            "package": package,
            "package_label": PACKAGE_LABELS.get(package, ""),
            "price_min": min(prices),
            "price_max": max(prices),
            "brand": produto["marca"] or "",
            "category": category,
"subcategory": subcategory,
            "classe_abc": produto.get("classe_abc") or "",
            "imagem_url": first_image(),
            "attrs": attr_cards,
            "brands": brands,
            "variants": variants_out,
            "variant_count": len(variants_out),
        }

    def _flat_card(
        self,
        row: dict,
        attrs: dict[int, dict],
        images: dict[int, list[str]],
        attr_defs: dict[int, list[dict]],
        suppliers: dict[int, list[str]] | None = None,
    ) -> dict:
        vattrs = attrs.get(row["id"], {})
        defs = attr_defs.get(row["familia_id"], [])
        package = row["embalagem"] or None
        spec_parts: list[str] = []
        if package:
            spec_parts.append(PACKAGE_LABELS.get(package, package) or package)
        for d in defs:
            val = vattrs.get(d["id"])
            if val:
                spec_parts.append(val)
        fns = images.get(row["produto_id"], [])
        return {
            "group": False,
            "id": row["id"],
            "sku": row["sku"] or "",
            "ean": row["ean"] or "",
            "name": row["nome"] or "",
            "base": row["nome"] or "",
            "spec": " Â· ".join(spec_parts),
            "package": package,
            "package_label": PACKAGE_LABELS.get(package, ""),
            "attrs": vattrs,
            "brand": row["marca_var"] or row["marca_prod"] or "",
            "price": row["preco"] or 0,
            "old_price": row["old_price"],
            "pix_price": row["pix_price"] or 0,
            "installment": row["installment"] or "",
            "category": row["categoria"] or "",
            "subcategory": row["subcategoria"] or "",
            "classe_abc": row["classe_abc"] or "",
            "unidade_venda": row["unidade_venda"] or "",
            "embalagem_qtd": row["embalagem_qtd"],
            "ncm": row["ncm"] or "",
            "imagem_url": image_url(fns[0]) if fns else None,
            "fornecedores": (suppliers or {}).get(row["id"], []),
        }

