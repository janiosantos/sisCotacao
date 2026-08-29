"""Repositório do catálogo — lê da base única (PostgreSQL).

O catálogo consome o cadastro de produtos (`produtos_cadastro`). No modelo
unificado cada produto é uma unidade independente (as antigas variações
tornaram-se produtos próprios) — não há mais `variantes` nem seletor de
variações; cada linha de `produtos_cadastro` é um item com seu próprio preço.
"""
from __future__ import annotations

import json

from catalog_server.db import system_conn
from catalog_server.grouping import PACKAGE_LABELS
from catalog_server.repositories.busca import montar_busca
from catalog_server.utils import image_url


def _parse_json_attrs(value) -> dict:
    """Coluna `produtos_cadastro.atributos` (JSONB) -> dict `{nome: valor}`."""
    if isinstance(value, dict):
        return value
    if isinstance(value, str) and value.strip():
        try:
            return json.loads(value)
        except ValueError:
            return {}
    return {}


def _order_abc(ordenar: str = "", prefix: str = "", extra: str = "") -> str:
    """Cláusula ORDER BY do catálogo; `ordenar="abc"` prioriza a Curva ABC (A→C)."""
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

    def list_products(
        self,
        categoria: str = "",
        subcategoria: str = "",
        grupo: str = "",
        q: str = "",
        classe: str = "",
        em_linha: bool = True,
        offset: int = 0,
        limit: int = 60,
        agrupado: bool = True,
        ordenar: str = "",
    ) -> tuple[list[dict], int]:
        """Retorna os itens do catálogo.

        No modelo unificado cada produto é uma unidade individual (cada antiga
        variação virou produto próprio). `agrupado` é mantido apenas por
        compatibilidade da assinatura — o comportamento é sempre "flat": um
        card por produto com seu próprio preço. `classe` filtra pela Curva ABC.
        `em_linha=True` (padrão) exclui equipamentos de alto valor marcados
        `em_linha=0`. `grupo` filtra pelo grupo (código ou nome, ex.: ELE/ELETRICO).
        """
        q = (q or "").strip()
        ordenar = (ordenar or "").strip().lower()
        with system_conn() as conn:
            rows, total = self._browse_flat(conn, categoria, subcategoria, grupo, q, classe, em_linha, offset, limit, ordenar)
            produto_ids = [r["id"] for r in rows]
            attr_defs = self._load_attr_defs(conn, [r["familia_id"] for r in rows])
            attrs = self._load_product_attrs(conn, produto_ids, attr_defs)
            images = self._load_images(conn, produto_ids)
            suppliers = self._load_variant_suppliers(conn, produto_ids)
            cards = [self._flat_card(r, attrs, images, attr_defs, suppliers) for r in rows]
        return cards, total

    def _browse_flat(
        self, conn, categoria: str, subcategoria: str, grupo: str, q: str, classe: str, em_linha: bool, offset: int, limit: int, ordenar: str = ""
    ) -> tuple[list[dict], int]:
        joins = (
            " LEFT JOIN familias f ON f.id=p.familia_id"
            " LEFT JOIN categorias cat ON cat.id=p.categoria_id"
            " LEFT JOIN subcategorias sub ON sub.id=p.subcategoria_id"
            " LEFT JOIN grupos grp ON grp.id=p.grupo_id"
        )
        where = ["p.ativo=1"]
        params: list = []
        order_params: list = []
        order_sql = ""
        if q:
            wq, pq, oex, opq = montar_busca(q)
            where.append(wq)
            params += pq
            order_sql = "ORDER BY " + oex
            order_params = opq
        else:
            order_sql = _order_abc(ordenar, extra="p.id")
        if categoria:
            where.append("cat.nome=?")
            params.append(categoria)
        if subcategoria:
            where.append("sub.nome=?")
            params.append(subcategoria)
        if grupo:
            where.append("(grp.codigo ILIKE ? OR grp.nome ILIKE ?)")
            params += [grupo, grupo]
        if classe:
            where.append("p.classe_abc=?")
            params.append(classe)
        if em_linha:
            where.append("p.em_linha=1")
        where_sql = " AND ".join(where)
        base = f" FROM produtos_cadastro p{joins} WHERE {where_sql}"

        total = conn.execute(
            f"SELECT COUNT(*) AS n{base}", params
        ).fetchone()["n"]
        rows = conn.execute(
            f"""
            SELECT p.id, p.id AS produto_id, p.sku, p.ean, p.preco, p.old_price,
                   p.pix_price, p.installment, p.marca AS marca_prod,
                   p.nome, p.marca AS marca_var, p.familia_id,
                   COALESCE(cat.nome, '') AS categoria,
                   COALESCE(sub.nome, '') AS subcategoria, p.embalagem,
                   COALESCE(grp.codigo, '') AS grupo_codigo,
                   COALESCE(grp.nome, '') AS grupo_nome,
                   p.classe_abc, p.ordem_abc,
                   p.unidade_venda, p.embalagem AS embalagem_qtd, p.ncm,
                   p.descricao
            {base}
            {order_sql}
            LIMIT ? OFFSET ?
            """,
            params + order_params + [limit, offset],
        ).fetchall()
        return [dict(r) for r in rows], total

    # ------------------------------------------------------------------
    # Ordenação / categorias
    # ------------------------------------------------------------------

    def categorias(self) -> dict[str, list[str]]:
        """Árvore categoria -> subcategorias, a partir da taxonomia normalizada.

        Só categorias com ao menos um produto ativo (em linha) aparecem.
        """
        with system_conn() as conn:
            pairs = conn.execute(
                """
                SELECT DISTINCT p.categoria_id, p.subcategoria_id
                FROM produtos_cadastro p
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

    def resumo_abc(
        self, categoria: str = "", subcategoria: str = "", grupo: str = "", q: str = "", em_linha: bool = True
    ) -> dict:
        """Contagem de produtos por classe ABC sob os mesmos filtros do catálogo."""
        q = (q or "").strip()
        joins = (
            " LEFT JOIN categorias cat ON cat.id=p.categoria_id"
            " LEFT JOIN subcategorias sub ON sub.id=p.subcategoria_id"
            " LEFT JOIN grupos grp ON grp.id=p.grupo_id"
        )
        where = ["p.ativo=1"]
        params: list = []
        if categoria:
            where.append("cat.nome=?")
            params.append(categoria)
        if subcategoria:
            where.append("sub.nome=?")
            params.append(subcategoria)
        if grupo:
            where.append("(grp.codigo ILIKE ? OR grp.nome ILIKE ?)")
            params += [grupo, grupo]
        if em_linha:
            where.append("p.em_linha=1")
        if q:
            like = f"%{q}%"
            where.append("(p.nome LIKE ? OR p.marca LIKE ? OR p.sku LIKE ? OR p.ean LIKE ?)")
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
        """Detalhe de um produto (id = produto)."""
        with system_conn() as conn:
            row = conn.execute(
                """
                SELECT p.*, p.nome, p.marca AS produto_marca,
                       cat.nome AS categoria, sub.nome AS subcategoria
                FROM produtos_cadastro p
                LEFT JOIN categorias cat ON cat.id=p.categoria_id
                LEFT JOIN subcategorias sub ON sub.id=p.subcategoria_id
                WHERE p.id=? AND p.ativo=1
                """,
                (product_id,),
            ).fetchone()
            if row is None:
                return None
            images = conn.execute(
                """
                SELECT filename FROM imagens_produto
                WHERE produto_id=?
                ORDER BY ordem, id
                """,
                (product_id,),
            ).fetchall()
            color = ""
            attrs = _parse_json_attrs(row["atributos"])
            for nome, valor in attrs.items():
                if "cor" in nome.lower():
                    color = valor
                    break

        return {
            "id": row["id"],
            "sku": row["sku"] or "",
            "ean": row["ean"] or "",
            "name": row["nome"] or "",
            "brand": row["produto_marca"] or row["marca"] or "",
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
        """Resolve ids de produto para enriquecer cotações/histórico."""
        if not ids:
            return {}
        out: dict[int, dict] = {}
        with system_conn() as conn:
            for chunk_start in range(0, len(ids), 500):
                chunk = ids[chunk_start : chunk_start + 500]
                placeholders = ",".join("?" * len(chunk))
                rows = conn.execute(
                    f"""
SELECT p.id, p.sku, p.preco, p.marca, p.external_id,
                           p.nome, p.marca AS produto_marca,
                           cat.nome AS categoria, sub.nome AS subcategoria,
                           (SELECT im.filename FROM imagens_produto im
                            WHERE im.produto_id=p.id
                            ORDER BY im.ordem, im.id LIMIT 1) AS imagem_filename
                    FROM produtos_cadastro p
                    LEFT JOIN categorias cat ON cat.id=p.categoria_id
                    LEFT JOIN subcategorias sub ON sub.id=p.subcategoria_id
                    WHERE p.id IN ({placeholders})
                    """,
                    chunk,
                ).fetchall()
                for r in rows:
                    out[r["id"]] = {
                        "id": r["id"],
                        "sku": r["sku"] or "",
                        "name": r["nome"] or "",
                        "brand": r["produto_marca"] or r["marca"] or "",
                        "category": r["categoria"] or "",
                        "subcategory": r["subcategoria"] or "",
                        "imagem_url": image_url(r["imagem_filename"]),
                        "price": r["preco"] or 0,
                    }
        return out

    # ------------------------------------------------------------------

    def products_with_history(self) -> list[dict]:
        """Produtos disponíveis para consulta de histórico."""
        with system_conn() as conn:
            rows = conn.execute(
                """
                SELECT p.id, p.sku, p.nome
                FROM produtos_cadastro p
                WHERE p.ativo=1
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
    def _load_product_attrs(conn, produto_ids: list[int], attr_defs: dict[int, list[dict]] | None = None) -> dict[int, dict]:
        """Lê os atributos dos produtos a partir do JSONB `produtos_cadastro.atributos`.

        O JSONB é indexado por **nome** do atributo; converte para o contrato do
        catálogo (indexado por **id**) usando as definições da família
        (`attr_defs`: familia_id -> [{id, label}]). Nomes sem id conhecido são
        mantidos como texto.
        """
        out: dict[int, dict] = {}
        if not produto_ids:
            return out
        placeholders = ",".join("?" * len(produto_ids))
        rows = conn.execute(
            f"""
            SELECT p.id, p.familia_id, p.atributos
            FROM produtos_cadastro p
            WHERE p.id IN ({placeholders})
            """,
            produto_ids,
        ).fetchall()
        for r in rows:
            name2id: dict[str, int] = {}
            familia_id = r["familia_id"]
            if attr_defs and familia_id in attr_defs:
                name2id = {d["label"]: int(d["id"]) for d in attr_defs[familia_id]}
            mapped: dict = {}
            for nome, valor in (_parse_json_attrs(r["atributos"]) or {}).items():
                key = name2id.get(nome)
                if key is None:
                    key = str(nome)
                mapped[key] = str(valor)
            out[r["id"]] = mapped
        return out

    @staticmethod
    def _load_variant_suppliers(conn, produto_ids: list[int]) -> dict[int, list[str]]:
        """Nome dos fornecedores mapeados para cada produto (códigos de compra)."""
        out: dict[int, list[str]] = {}
        if not produto_ids:
            return out
        placeholders = ",".join("?" * len(produto_ids))
        rows = conn.execute(
            f"""
            SELECT fv.produto_id, s.nome
            FROM fornecedor_variantes fv
            JOIN fornecedores s ON s.id=fv.fornecedor_id
            WHERE fv.produto_id IN ({placeholders})
            ORDER BY s.nome
            """,
            produto_ids,
        ).fetchall()
        for r in rows:
            out.setdefault(r["produto_id"], []).append(r["nome"])
        return out

    @staticmethod
    def _load_images(conn, produto_ids: list[int]) -> dict[int, list[str]]:
        out: dict[int, list[str]] = {}
        if not produto_ids:
            return out
        placeholders = ",".join("?" * len(produto_ids))
        rows = conn.execute(
            f"""
            SELECT produto_id, filename
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
    # Montagem dos cards (flat — um card por produto)
    # ------------------------------------------------------------------

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
        if package and str(package).strip() not in ("", "1"):
            spec_parts.append(PACKAGE_LABELS.get(package, package) or package)
        for d in defs:
            val = vattrs.get(d["id"])
            if val:
                spec_parts.append(val)
        # `spec` = características DISTINTIVAS (embalagem + atributos + marca +
        # unidade) — permite identificar a variante na busca rápida (o nome já
        # aparece separado). A descricao (etiqueta completa) é exposta à parte.
        marca = (row["marca_prod"] or row["marca_var"] or "").strip()
        unidade = (row.get("unidade_venda") or "").strip()
        for extra in (marca, unidade):
            if extra and extra not in spec_parts:
                spec_parts.append(extra)
        spec = " · ".join(spec_parts)
        fns = images.get(row["produto_id"], [])
        return {
            "group": False,
            "id": row["id"],
            "sku": row["sku"] or "",
            "ean": row["ean"] or "",
            "name": row["nome"] or "",
            "base": row["nome"] or "",
            "spec": spec,
            "descricao": (row.get("descricao") or "").strip(),
            "package": package,
            "package_label": PACKAGE_LABELS.get(package, ""),
            "attrs": vattrs,
            "brand": row["marca_prod"] or row["marca_var"] or "",
            "price": row["preco"] or 0,
            "old_price": row["old_price"],
            "pix_price": row["pix_price"] or 0,
            "installment": row["installment"] or "",
            "category": row["categoria"] or "",
            "subcategory": row["subcategoria"] or "",
            "grupo": row.get("grupo_codigo") or "",
            "grupo_nome": row.get("grupo_nome") or "",
            "classe_abc": row["classe_abc"] or "",
            "unidade_venda": row["unidade_venda"] or "",
            "embalagem_qtd": row["embalagem_qtd"],
            "ncm": row["ncm"] or "",
            "imagem_url": image_url(fns[0]) if fns else None,
            "fornecedores": (suppliers or {}).get(row["id"], []),
        }
