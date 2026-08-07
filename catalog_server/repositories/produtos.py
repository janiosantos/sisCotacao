"""Repositório do cadastro de produtos (famílias, produtos, variações, imagens).

Modelo inspirado no Protheus (TOTVS): uma família (SBP) tem características
(SBQ) com opções (SBS); um produto cadastrado pertence a uma família e suas
variações (SKUs) são combinações de valores dessas características.
"""
from __future__ import annotations

import json

from catalog_server import fts
from catalog_server import categorias
from catalog_server.db import system_conn


def _to_float(value):
    try:
        if value in (None, ""):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _list_atributos(conn, familia_id: int) -> list[dict]:
    rows = conn.execute(
        "SELECT * FROM familia_atributos WHERE familia_id=? ORDER BY ordem, id",
        (familia_id,),
    ).fetchall()
    out = []
    for r in rows:
        d = dict(r)
        try:
            d["opcoes"] = json.loads(d["opcoes"] or "[]")
        except ValueError:
            d["opcoes"] = []
        out.append(d)
    return out


class ProdutoRepository:

    # ------------------------------------------------------------------
    # Famílias
    # ------------------------------------------------------------------

    def list_familias(self, incluir_inativas: bool = False) -> list[dict]:
        sql = "SELECT * FROM familias"
        if not incluir_inativas:
            sql += " WHERE ativo=1"
        sql += " ORDER BY nome"
        with system_conn() as conn:
            fams = [dict(r) for r in conn.execute(sql).fetchall()]
            for f in fams:
                f["atributos"] = _list_atributos(conn, f["id"])
            return fams

    def get_familia(self, familia_id: int) -> dict | None:
        with system_conn() as conn:
            row = conn.execute(
                "SELECT * FROM familias WHERE id=?", (familia_id,)
            ).fetchone()
            if row is None:
                return None
            f = dict(row)
            f["atributos"] = _list_atributos(conn, familia_id)
            return f

    def create_familia(self, nome: str, descricao: str, atributos: list[dict]) -> int:
        with system_conn() as conn:
            cur = conn.execute(
                "INSERT INTO familias (nome, descricao) VALUES (?,?)",
                (nome, descricao or ""),
            )
            familia_id = cur.lastrowid
            self._replace_atributos(conn, familia_id, atributos)
            return familia_id

    def update_familia(self, familia_id: int, nome: str, descricao: str, atributos: list[dict]) -> bool:
        with system_conn() as conn:
            cur = conn.execute(
                "UPDATE familias SET nome=?, descricao=? WHERE id=?",
                (nome, descricao or "", familia_id),
            )
            if cur.rowcount == 0:
                return False
            self._replace_atributos(conn, familia_id, atributos)
            return True

    def count_products(self, familia_id: int) -> int:
        with system_conn() as conn:
            row = conn.execute(
                "SELECT COUNT(*) AS n FROM produtos_cadastro WHERE familia_id=?",
                (familia_id,),
            ).fetchone()
            return row["n"]

    def delete_familia(self, familia_id: int) -> bool:
        with system_conn() as conn:
            cur = conn.execute("DELETE FROM familias WHERE id=?", (familia_id,))
            return cur.rowcount > 0

    def _replace_atributos(self, conn, familia_id: int, atributos: list[dict]) -> None:
        if not atributos:
            return
        existing = {
            r["id"]: r
            for r in conn.execute(
                "SELECT * FROM familia_atributos WHERE familia_id=?", (familia_id,)
            ).fetchall()
        }
        submitted = set()
        for ordem, a in enumerate(atributos, start=1):
            nome = (a.get("nome") or "").strip()
            if not nome:
                continue
            tipo = a.get("tipo") if a.get("tipo") in ("lista", "livre") else "lista"
            opcoes = json.dumps(a.get("opcoes") or [], ensure_ascii=False)
            obrigatorio = 1 if a.get("obrigatorio") else 0
            aid = a.get("id")
            if aid in existing:
                submitted.add(aid)
                conn.execute(
                    "UPDATE familia_atributos SET nome=?, tipo=?, opcoes=?, obrigatorio=?, ordem=? WHERE id=?",
                    (nome, tipo, opcoes, obrigatorio, ordem, aid),
                )
            else:
                cur = conn.execute(
                    "INSERT INTO familia_atributos (familia_id, nome, tipo, opcoes, obrigatorio, ordem)"
                    " VALUES (?,?,?,?,?,?)",
                    (familia_id, nome, tipo, opcoes, obrigatorio, ordem),
                )
                submitted.add(cur.lastrowid)
        for aid in set(existing) - submitted:
            conn.execute("DELETE FROM familia_atributos WHERE id=?", (aid,))

    # ------------------------------------------------------------------
    # Produtos (pai)
    # ------------------------------------------------------------------

    def list_products(
        self,
        q: str = "",
        familia_id: int | None = None,
        offset: int = 0,
        limit: int = 60,
    ) -> tuple[list[dict], int]:
        q = (q or "").strip()
        with system_conn() as conn:
            fts.ensure_fts(conn)
            if q and not fts.is_empty(conn):
                return self._search_fts(conn, q, familia_id, offset, limit)
            return self._browse(conn, q, familia_id, offset, limit)

    def _browse(
        self,
        conn,
        q: str = "",
        familia_id: int | None = None,
        offset: int = 0,
        limit: int = 60,
    ) -> tuple[list[dict], int]:
        where = ["1=1"]
        params: list = []
        if q:
            like = f"%{q}%"
            where.append("(p.nome LIKE ? OR p.marca LIKE ? OR f.nome LIKE ?)")
            params += [like, like, like]
        if familia_id:
            where.append("p.familia_id=?")
            params.append(familia_id)
        where_sql = " AND ".join(where)

        total = conn.execute(
            f"SELECT COUNT(*) AS n FROM produtos_cadastro p LEFT JOIN familias f ON f.id=p.familia_id WHERE {where_sql}",
            params,
        ).fetchone()["n"]
        from_sql = f"FROM produtos_cadastro p LEFT JOIN familias f ON f.id=p.familia_id WHERE {where_sql}"
        rows = self._select_rows(conn, from_sql, params, offset, limit)
        return [dict(r) for r in rows], total

    def _search_fts(
        self,
        conn,
        q: str,
        familia_id: int | None,
        offset: int,
        limit: int,
    ) -> tuple[list[dict], int]:
        match = fts.search_query(q)
        if not match:
            return [], 0
        where = "produtos_fts MATCH ?"
        params: list = [match]
        if familia_id:
            where += " AND p.familia_id=?"
            params.append(familia_id)

        total = conn.execute(
            f"SELECT COUNT(*) AS n FROM produtos_fts ft JOIN produtos_cadastro p ON p.id=ft.produto_id"
            f" WHERE {where}",
            params,
        ).fetchone()["n"]
        from_sql = f"FROM produtos_fts ft JOIN produtos_cadastro p ON p.id=ft.produto_id"
        from_sql += f" LEFT JOIN familias f ON f.id=p.familia_id WHERE {where}"
        rows = self._select_rows(conn, from_sql, params, offset, limit, order_by="bm25(produtos_fts)")
        return [dict(r) for r in rows], total

    def _select_rows(self, conn, from_sql: str, params: list, offset: int, limit: int, order_by: str = "") -> list:
        """SELECT das linhas de produtos com as colunas de card (variações/preço/foto).

        `from_sql` é a cláusula `FROM ... [JOIN ...] WHERE ...` completa.
        """
        order = order_by or "p.nome COLLATE NOCASE"
        return conn.execute(
            f"""
            SELECT p.*, f.nome AS familia_nome,
                   (SELECT COUNT(*) FROM variantes v
                    WHERE v.produto_id=p.id AND v.ativo=1) AS variant_count,
                   (SELECT MIN(preco) FROM variantes v
                    WHERE v.produto_id=p.id AND v.ativo=1 AND preco>0) AS price_min,
                   (SELECT MAX(preco) FROM variantes v
                    WHERE v.produto_id=p.id AND v.ativo=1 AND preco>0) AS price_max,
                   (SELECT filename FROM imagens_produto im
                    WHERE im.produto_id=p.id
                    ORDER BY (im.variante_id IS NOT NULL), im.ordem, im.id LIMIT 1) AS imagem_filename
            {from_sql}
            ORDER BY {order}, p.nome COLLATE NOCASE, p.id
            LIMIT ? OFFSET ?
            """,
            params + [limit, offset],
        ).fetchall()

    def get_product(self, produto_id: int) -> dict | None:
        with system_conn() as conn:
            row = conn.execute(
                "SELECT p.*, f.nome AS familia_nome,"
                " COALESCE(cat.nome,'') AS categoria, COALESCE(sub.nome,'') AS subcategoria"
                " FROM produtos_cadastro p"
                " LEFT JOIN familias f ON f.id=p.familia_id"
                " LEFT JOIN categorias cat ON cat.id=p.categoria_id"
                " LEFT JOIN subcategorias sub ON sub.id=p.subcategoria_id"
                " WHERE p.id=?",
                (produto_id,),
            ).fetchone()
            if row is None:
                return None
            prod = dict(row)
            prod["atributos"] = _list_atributos(conn, prod["familia_id"])
            nome_por_id = {str(a["id"]): a["nome"] for a in prod["atributos"]}

            vrows = conn.execute(
                "SELECT * FROM variantes WHERE produto_id=? ORDER BY id",
                (produto_id,),
            ).fetchall()
            variants = []
            for v in vrows:
                vd = dict(v)
                avals = conn.execute(
                    "SELECT atributo_id, valor FROM variante_atributos WHERE variante_id=?",
                    (v["id"],),
                ).fetchall()
                vd["atributos"] = {str(a["atributo_id"]): a["valor"] for a in avals}
                vd["atributos_nomes"] = {
                    nome_por_id[str(a["atributo_id"])]: a["valor"] for a in avals
                }
                variants.append(vd)
            prod["variantes"] = variants

            imgs = conn.execute(
                "SELECT * FROM imagens_produto WHERE produto_id=? ORDER BY ordem, id",
                (produto_id,),
            ).fetchall()
            prod["imagens"] = [dict(i) for i in imgs]
            prod["fornecedor_variantes"] = self.get_fornecedor_variantes(conn, produto_id)
            return prod

    def create_product(
        self,
        familia_id: int,
        nome: str,
        marca: str,
        descricao: str,
        categoria: str,
        variantes: list[dict],
        subcategoria: str = "",
        termos_busca: str = "",
    ) -> int:
        with system_conn() as conn:
            categoria_id, subcategoria_id = categorias.resolve(conn, categoria, subcategoria)
            cur = conn.execute(
                "INSERT INTO produtos_cadastro"
                " (familia_id, nome, marca, descricao, termos_busca, categoria_id, subcategoria_id)"
                " VALUES (?,?,?,?,?,?,?)",
                (
                    familia_id,
                    nome,
                    marca or "",
                    descricao or "",
                    termos_busca or "",
                    categoria_id,
                    subcategoria_id,
                ),
            )
            produto_id = cur.lastrowid
            self._replace_variantes(conn, produto_id, variantes)
            fts.sync_product(conn, produto_id)
            return produto_id

    def update_product(
        self,
        produto_id: int,
        familia_id: int,
        nome: str,
        marca: str,
        descricao: str,
        categoria: str,
        variantes: list[dict],
        subcategoria: str = "",
        termos_busca: str = "",
    ) -> bool:
        with system_conn() as conn:
            categoria_id, subcategoria_id = categorias.resolve(conn, categoria, subcategoria)
            cur = conn.execute(
                "UPDATE produtos_cadastro SET familia_id=?, nome=?, marca=?, descricao=?,"
                " termos_busca=?, categoria_id=?, subcategoria_id=?, atualizado_em=datetime('now') WHERE id=?",
                (
                    familia_id,
                    nome,
                    marca or "",
                    descricao or "",
                    termos_busca or "",
                    categoria_id,
                    subcategoria_id,
                    produto_id,
                ),
            )
            if cur.rowcount == 0:
                return False
            self._replace_variantes(conn, produto_id, variantes)
            fts.sync_product(conn, produto_id)
            return True

    def delete_product(self, produto_id: int) -> bool:
        with system_conn() as conn:
            cur = conn.execute("DELETE FROM produtos_cadastro WHERE id=?", (produto_id,))
            if cur.rowcount == 0:
                return False
            fts.delete_product(conn, produto_id)
            return True

    def _replace_variantes(self, conn, produto_id: int, variantes: list[dict]) -> None:
        existing = {
            r["id"]
            for r in conn.execute(
                "SELECT id FROM variantes WHERE produto_id=?", (produto_id,)
            ).fetchall()
        }
        submitted = set()
        for v in variantes or []:
            preco = _to_float(v.get("preco"))
            prom = _to_float(v.get("preco_promocional"))
            attrs = v.get("atributos") or {}
            vid = v.get("id")
            if vid in existing:
                submitted.add(vid)
                conn.execute(
                    "UPDATE variantes SET sku=?, ean=?, preco=?, preco_promocional=?,"
                    " observacao=? WHERE id=? AND produto_id=?",
                    (
                        v.get("sku") or "",
                        v.get("ean") or "",
                        preco or 0,
                        prom,
                        v.get("observacao") or "",
                        vid,
                        produto_id,
                    ),
                )
            else:
                cur = conn.execute(
                    "INSERT INTO variantes (produto_id, sku, ean, preco, preco_promocional, observacao)"
                    " VALUES (?,?,?,?,?,?)",
                    (
                        produto_id,
                        v.get("sku") or "",
                        v.get("ean") or "",
                        preco or 0,
                        prom,
                        v.get("observacao") or "",
                    ),
                )
                vid = cur.lastrowid
                submitted.add(vid)
            conn.execute("DELETE FROM variante_atributos WHERE variante_id=?", (vid,))
            for aid, valor in attrs.items():
                if valor in (None, ""):
                    continue
                conn.execute(
                    "INSERT INTO variante_atributos (variante_id, atributo_id, valor) VALUES (?,?,?)",
                    (vid, int(aid), str(valor)),
                )
        for vid in existing - submitted:
            conn.execute("DELETE FROM variantes WHERE id=?", (vid,))

    # ------------------------------------------------------------------
    # Imagens
    # ------------------------------------------------------------------

    def add_imagem(
        self,
        produto_id: int,
        filename: str,
        url_origem: str = "",
        variante_id: int | None = None,
    ) -> int:
        with system_conn() as conn:
            row = conn.execute(
                "SELECT COALESCE(MAX(ordem), -1) + 1 AS n FROM imagens_produto WHERE produto_id=?",
                (produto_id,),
            ).fetchone()
            cur = conn.execute(
                "INSERT INTO imagens_produto (produto_id, variante_id, filename, url_origem, ordem)"
                " VALUES (?,?,?,?,?)",
                (produto_id, variante_id, filename, url_origem or "", row["n"]),
            )
            return cur.lastrowid

    def delete_imagem(self, imagem_id: int) -> dict | None:
        with system_conn() as conn:
            row = conn.execute(
                "SELECT * FROM imagens_produto WHERE id=?", (imagem_id,)
            ).fetchone()
            if row is None:
                return None
            data = dict(row)
            conn.execute("DELETE FROM imagens_produto WHERE id=?", (imagem_id,))
            return data

    def set_imagem_capa(self, produto_id: int, imagem_id: int) -> bool:
        """Define a imagem como capa (ordem 0), reordenando as demais."""
        with system_conn() as conn:
            row = conn.execute(
                "SELECT id FROM imagens_produto WHERE id=? AND produto_id=?",
                (imagem_id, produto_id),
            ).fetchone()
            if row is None:
                return False
            others = [
                r["id"]
                for r in conn.execute(
                    "SELECT id FROM imagens_produto WHERE produto_id=? AND id<>? ORDER BY ordem, id",
                    (produto_id, imagem_id),
                ).fetchall()
            ]
            conn.execute(
                "UPDATE imagens_produto SET ordem=? WHERE id=?",
                (0, imagem_id),
            )
            for i, oid in enumerate(others, start=1):
                conn.execute(
                    "UPDATE imagens_produto SET ordem=? WHERE id=?",
                    (i, oid),
                )
            return True

    # ------------------------------------------------------------------
    # Fornecedor x Variante (códigos, unidade de compra, fator de conversão)
    # ------------------------------------------------------------------

    def get_fornecedor_variantes(self, conn, produto_id: int | None) -> list[dict]:
        """Mapeamentos fornecedor x variante de um produto (junto do nome do fornecedor)."""
        if produto_id is None:
            return []
        rows = conn.execute(
            "SELECT fv.variante_id, fv.fornecedor_id, fv.codigo_fornecedor,"
            " fv.descricao_fornecedor, fv.unidade_compra, fv.fator_conversao,"
            " s.nome AS fornecedor_nome, v.sku"
            " FROM fornecedor_variantes fv"
            " JOIN fornecedores s ON s.id=fv.fornecedor_id"
            " JOIN variantes v ON v.id=fv.variante_id"
            " WHERE fv.variante_id IN"
            "   (SELECT id FROM variantes WHERE produto_id=?)"
            " ORDER BY s.nome, fv.variante_id",
            (produto_id,),
        ).fetchall()
        return [dict(r) for r in rows]

    def save_fornecedor_variantes(
        self, conn, fornecedor_id: int, produto_id: int, itens: list[dict]
    ) -> int:
        """Substitui os mapeamentos de um fornecedor para as variantes de um produto."""
        variante_ids = [
            r["id"]
            for r in conn.execute(
                "SELECT id FROM variantes WHERE produto_id=?", (produto_id,)
            ).fetchall()
        ]
        if not variante_ids:
            return 0
        marks = ",".join("?" for _ in variante_ids)
        conn.execute(
            "DELETE FROM fornecedor_variantes WHERE fornecedor_id=? AND variante_id IN (" + marks + ")",
            [fornecedor_id] + variante_ids,
        )
        count = 0
        for item in itens or []:
            vid = item.get("variante_id")
            if vid not in variante_ids:
                continue
            codigo = str(item.get("codigo_fornecedor") or "").strip()
            unidade = str(item.get("unidade_compra") or "").strip()
            fator = _to_float(item.get("fator_conversao"))
            conn.execute(
                "INSERT INTO fornecedor_variantes (variante_id, fornecedor_id,"
                " codigo_fornecedor, descricao_fornecedor, unidade_compra, fator_conversao)"
                " VALUES (?,?,?,?,?,?)",
                (
                    vid,
                    fornecedor_id,
                    codigo,
                    str(item.get("descricao_fornecedor") or "").strip(),
                    unidade,
                    fator if fator is not None else 1,
                ),
            )
            count += 1
        return count
