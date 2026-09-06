"""Repositório do cadastro de produtos (famílias, produtos, imagens).

Modelo inspirado no Protheus (TOTVS): uma família (SBP) tem características
(SBQ) com opções (SBS). Cada linha de `produtos_cadastro` é um produto
independente (no modelo unificado, cada antiga variação tornou-se um produto
próprio — não há mais tabela `variantes`). Os atributos do produto vivem no
JSONB `produtos_cadastro.atributos`.
"""
from __future__ import annotations

import json

from catalog_server import categorias
from catalog_server.db import system_conn
from catalog_server.repositories import marcas
from catalog_server.repositories.busca import montar_busca
from catalog_server.services.sku_service import (
    codigo_familia,
    codigo_produto,
    normalizar as normalizar_sku,
    reservar as reservar_sku,
    sku_emitido as sku_emitido_variante,
)


def _parse_json_attrs(value) -> dict:
    """Coluna `produtos_cadastro.atributos` (JSONB) -> dict.

    No Postgres o psycopg devolve o JSONB já decodificado (dict); normaliza
    para `{nome: valor}`.
    """
    if isinstance(value, dict):
        return value
    if isinstance(value, str) and value.strip():
        try:
            return json.loads(value)
        except ValueError:
            return {}
    return {}


def _to_float(value):
    try:
        if value in (None, ""):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _to_int(value):
    try:
        if value in (None, ""):
            return None
        return int(float(value))
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


def _contexto_sku(conn, grupo_id: int | None, subgrupo_id: int | None, familia_id: int | None, produto_id: int) -> tuple[str, str, str]:
    """Resolve códigos da taxonomia no backend, sem confiar no frontend."""
    row = conn.execute(
        "SELECT COALESCE(g.codigo, '') AS grupo_codigo,"
        " COALESCE(sg.codigo, '') AS subgrupo_codigo"
        " FROM (SELECT 1) x"
        " LEFT JOIN grupos g ON g.id=?"
        " LEFT JOIN subgrupos sg ON sg.id=?",
        (grupo_id, subgrupo_id),
    ).fetchone()
    grupo_cod = row["grupo_codigo"] if row else ""
    subgrupo_cod = row["subgrupo_codigo"] if row else ""
    if not (grupo_cod or subgrupo_cod or familia_id):
        return "", "", ""
    if familia_id:
        # Ordinal estável da família dentro do grupo/subgrupo (1, 2, 3…) —
        # não depende do id global da família; variações da mesma família
        # compartilham o núcleo e diferem pelo sufixo numérico.
        seq = conn.execute(
            """SELECT COUNT(*) + 1 AS seq FROM (
                   SELECT p.familia_id, MIN(p.id) AS first_id
                   FROM produtos_cadastro p
                   WHERE p.grupo_id=? AND p.subgrupo_id=? AND p.familia_id IS NOT NULL
                   GROUP BY p.familia_id
               ) f0
               WHERE f0.first_id < (SELECT COALESCE(MIN(p2.id),0) FROM produtos_cadastro p2 WHERE p2.familia_id=?)""",
            (grupo_id, subgrupo_id, familia_id),
        ).fetchone()["seq"]
        familia_cod = f"{int(seq or 1):03d}"
    else:
        familia_cod = codigo_produto(produto_id)
    return grupo_cod, subgrupo_cod, familia_cod


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
                self._normalize_sku_template(f)
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
            self._normalize_sku_template(f)
            return f

    @staticmethod
    def _normalize_sku_template(f: dict) -> None:
        raw = f.get("sku_atributos")
        if isinstance(raw, str) and raw.strip():
            try:
                raw = json.loads(raw)
            except ValueError:
                raw = None
        if isinstance(raw, list):
            f["sku_atributos"] = [str(x) for x in raw if str(x).strip()]
        else:
            f["sku_atributos"] = None

    def create_familia(self, nome: str, descricao: str, atributos: list[dict], ncm_padrao: str = "", unidade_padrao: str = "", sku_atributos: list[str] | None = None) -> int:
        with system_conn() as conn:
            cur = conn.execute(
                "INSERT INTO familias (nome, descricao, ncm_padrao, unidade_padrao, sku_atributos) VALUES (?,?,?,?,?)",
                (nome, descricao or "", ncm_padrao or "", unidade_padrao or "UN", json.dumps([str(x) for x in (sku_atributos or [])], ensure_ascii=False) if sku_atributos else None),
            )
            familia_id = cur.lastrowid
            self._replace_atributos(conn, familia_id, atributos)
            return familia_id

    def update_familia(self, familia_id: int, nome: str, descricao: str, atributos: list[dict], ncm_padrao: str = "", unidade_padrao: str = "", sku_atributos: list[str] | None = None) -> bool:
        with system_conn() as conn:
            cur = conn.execute(
                "UPDATE familias SET nome=?, descricao=?, ncm_padrao=?, unidade_padrao=?, sku_atributos=? WHERE id=?",
                (nome, descricao or "", ncm_padrao or "", unidade_padrao or "UN", json.dumps([str(x) for x in (sku_atributos or [])], ensure_ascii=False) if sku_atributos else None, familia_id),
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
            validacao = a.get("validacao") if a.get("validacao") in ("texto", "numero", "alphanumerico") else "texto"
            aid = a.get("id")
            if aid in existing:
                submitted.add(aid)
                conn.execute(
                    "UPDATE familia_atributos SET nome=?, tipo=?, opcoes=?, obrigatorio=?, ordem=?, validacao=? WHERE id=?",
                    (nome, tipo, opcoes, obrigatorio, ordem, validacao, aid),
                )
            else:
                cur = conn.execute(
                    "INSERT INTO familia_atributos (familia_id, nome, tipo, opcoes, obrigatorio, ordem, validacao)"
                    " VALUES (?,?,?,?,?,?,?)",
                    (familia_id, nome, tipo, opcoes, obrigatorio, ordem, validacao),
                )
                submitted.add(cur.lastrowid)
        for aid in set(existing) - submitted:
            conn.execute("DELETE FROM familia_atributos WHERE id=?", (aid,))

    # ------------------------------------------------------------------
    # Produtos
    # ------------------------------------------------------------------

    def list_products(
        self,
        q: str = "",
        familia_id: int | None = None,
        categoria: str = "",
        subcategoria: str = "",
        grupo_id: int | None = None,
        subgrupo_id: int | None = None,
        categoria_id: int | None = None,
        subcategoria_id: int | None = None,
        status_cadastro: str = "",
        offset: int = 0,
        limit: int = 60,
    ) -> tuple[list[dict], int]:
        q = (q or "").strip()
        with system_conn() as conn:
            return self._browse(
                conn,
                q,
                familia_id,
                categoria,
                subcategoria,
                grupo_id,
                subgrupo_id,
                categoria_id,
                subcategoria_id,
                status_cadastro,
                offset,
                limit,
            )

    def _browse(
        self,
        conn,
        q: str = "",
        familia_id: int | None = None,
        categoria: str = "",
        subcategoria: str = "",
        grupo_id: int | None = None,
        subgrupo_id: int | None = None,
        categoria_id: int | None = None,
        subcategoria_id: int | None = None,
        status_cadastro: str = "",
        offset: int = 0,
        limit: int = 60,
    ) -> tuple[list[dict], int]:
        joins_cat = " LEFT JOIN familias f ON f.id=p.familia_id" \
            " LEFT JOIN categorias cat ON cat.id=p.categoria_id" \
            " LEFT JOIN subcategorias sub ON sub.id=p.subcategoria_id" \
            " LEFT JOIN grupos g ON g.id=p.grupo_id" \
            " LEFT JOIN subgrupos sg ON sg.id=p.subgrupo_id"
        where = ["1=1"]
        params: list = []
        order_params: list = []
        order_sql = ""
        if q:
            wq, pq, oq, opq = montar_busca(q)
            where.append(wq)
            params += pq
            order_sql = oq
            order_params = opq
        if familia_id:
            where.append("p.familia_id=?")
            params.append(familia_id)
        if categoria:
            where.append("cat.nome=?")
            params.append(categoria)
        if subcategoria:
            where.append("sub.nome=?")
            params.append(subcategoria)
        if grupo_id:
            where.append("p.grupo_id=?")
            params.append(grupo_id)
        if subgrupo_id:
            where.append("p.subgrupo_id=?")
            params.append(subgrupo_id)
        if categoria_id:
            where.append("p.categoria_id=?")
            params.append(categoria_id)
        if subcategoria_id:
            where.append("p.subcategoria_id=?")
            params.append(subcategoria_id)
        if status_cadastro:
            where.append("COALESCE(p.status_cadastro, 'publicado')=?")
            params.append(status_cadastro)
        where_sql = " AND ".join(where)

        total = conn.execute(
            f"SELECT COUNT(*) AS n FROM produtos_cadastro p{joins_cat} WHERE {where_sql}",
            params,
        ).fetchone()["n"]
        from_sql = f"FROM produtos_cadastro p{joins_cat} WHERE {where_sql}"
        rows = self._select_rows(conn, from_sql, params + order_params, offset, limit, order_by=order_sql)
        return [dict(r) for r in rows], total

    def _select_rows(self, conn, from_sql: str, params: list, offset: int, limit: int, order_by: str = "") -> list:
        """SELECT das linhas de produtos com as colunas de card (preço/foto).

        No modelo unificado cada produto já carrega os próprios dados
        operacionais (preço, sku, etc.) — não há mais subconsultas em
        `variantes`.
        """
        order = order_by or "p.nome COLLATE NOCASE, p.id"
        return conn.execute(
            f"""
            SELECT p.*, COALESCE(p.atualizado_em, '') AS versao_edicao,
                   f.nome AS familia_nome,
                   COALESCE(cat.nome,'') AS categoria,
                   COALESCE(sub.nome,'') AS subcategoria,
                   COALESCE(g.codigo,'') AS grupo_codigo,
                   COALESCE(g.nome,'') AS grupo,
                   COALESCE(sg.codigo,'') AS subgrupo_codigo,
                   COALESCE(sg.nome,'') AS subgrupo,
                   (CASE WHEN p.preco IS NOT NULL AND p.preco > 0
                         THEN p.preco END) AS price_min,
                   (CASE WHEN p.preco IS NOT NULL AND p.preco > 0
                         THEN p.preco END) AS price_max,
                   (SELECT filename FROM imagens_produto im
                    WHERE im.produto_id=p.id
                    ORDER BY im.ordem, im.id LIMIT 1) AS imagem_filename
            {from_sql}
            ORDER BY {order}
            LIMIT ? OFFSET ?
            """,
            params + [limit, offset],
        ).fetchall()

    def get_product(self, produto_id: int) -> dict | None:
        with system_conn() as conn:
            row = conn.execute(
                "SELECT p.*, f.nome AS familia_nome,"
                " COALESCE(cat.nome,'') AS categoria, COALESCE(sub.nome,'') AS subcategoria,"
                " COALESCE(g.codigo,'') AS grupo_codigo, COALESCE(g.nome,'') AS grupo,"
                " COALESCE(sg.codigo,'') AS subgrupo_codigo, COALESCE(sg.nome,'') AS subgrupo,"
                " COALESCE(m.codigo,'') AS marca_codigo"
                " FROM produtos_cadastro p"
                " LEFT JOIN familias f ON f.id=p.familia_id"
                " LEFT JOIN categorias cat ON cat.id=p.categoria_id"
                " LEFT JOIN subcategorias sub ON sub.id=p.subcategoria_id"
                " LEFT JOIN grupos g ON g.id=p.grupo_id"
                " LEFT JOIN subgrupos sg ON sg.id=p.subgrupo_id"
                " LEFT JOIN marcas m ON m.id=p.marca_id"
                " WHERE p.id=?",
                (produto_id,),
            ).fetchone()
            if row is None:
                return None
            prod = dict(row)
            # `atributos` mantém as DEFINIÇÕES de atributos da família (contrato
            # do frontend). Os VALORES do produto (JSONB) vão em atributos_valores.
            valores = _parse_json_attrs(prod.get("atributos"))
            prod["atributos"] = _list_atributos(conn, prod["familia_id"])
            prod["atributos_valores"] = valores
            nome_por_id = {str(a["id"]): a["nome"] for a in prod["atributos"]}
            prod["atributos_nomes"] = {
                nome_por_id.get(k, k): v for k, v in valores.items()
            }
            imgs = conn.execute(
                "SELECT * FROM imagens_produto WHERE produto_id=? ORDER BY ordem, id",
                (produto_id,),
            ).fetchall()
            prod["imagens"] = [dict(i) for i in imgs]
            prod["fornecedor_variantes"] = self.get_fornecedor_variantes(conn, produto_id)
            return prod

    def create_product(
        self,
        familia_id: int | None,
        nome: str,
        marca: str,
        descricao: str,
        categoria: str,
        subcategoria: str = "",
        termos_busca: str = "",
        external_id: str | None = None,
        grupo_id: int | None = None,
        subgrupo_id: int | None = None,
        dados: dict | None = None,
        atributos: dict | None = None,
    ) -> int:
        dados = dados or {}
        atributos = atributos or {}
        with system_conn() as conn:
            categoria_id, subcategoria_id = categorias.resolve(
                conn, categoria, subcategoria, subgrupo_id
            )
            grupo_id, subgrupo_id, categoria_id, subcategoria_id = categorias.validar_hierarquia(
                conn, grupo_id, subgrupo_id, categoria_id, subcategoria_id
            )
            marca_id = marcas.resolver(conn, marca)
            cur = conn.execute(
                "INSERT INTO produtos_cadastro"
                " (familia_id, nome, marca, marca_id, descricao, termos_busca, categoria_id, subcategoria_id, external_id, grupo_id, subgrupo_id,"
                "  sku, ean, preco, preco_promocional, old_price, pix_price, custo_unitario, preco_venda, ncm,"
                "  peso, dimensoes, unidade_venda, embalagem, fator_conversao, localizacao, unidade_tributavel,"
                "  atributos, bitola, tensao, potencia, comprimento, diametro, rosca, material, cor, norma,"
                "  validade_dias, garantia_dias)"
                " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    familia_id,
                    nome,
                    marca or "",
                    marca_id,
                    descricao or "",
                    termos_busca or "",
                    categoria_id,
                    subcategoria_id,
                    str(external_id).strip() if external_id else None,
                    grupo_id,
                    subgrupo_id,
                    dados.get("sku") or "",
                    dados.get("ean") or "",
                    _to_float(dados.get("preco")) or 0,
                    _to_float(dados.get("preco_promocional")),
                    _to_float(dados.get("old_price")),
                    _to_float(dados.get("pix_price")),
                    _to_float(dados.get("custo_unitario")),
                    _to_float(dados.get("preco_venda")),
                    (dados.get("ncm") or "").strip(),
                    _to_float(dados.get("peso")) or 0,
                    dados.get("dimensoes") or "",
                    (dados.get("unidade_venda") or "UN").strip(),
                    _to_float(dados.get("embalagem")) or 1,
                    _to_float(dados.get("fator_conversao")) or 1,
                    dados.get("localizacao") or "",
                    (dados.get("unidade_tributavel") or "").strip(),
                    json.dumps({str(k): str(v) for k, v in atributos.items() if v not in (None, "")}, ensure_ascii=False),
                    (dados.get("bitola") or "").strip(),
                    (dados.get("tensao") or "").strip(),
                    (dados.get("potencia") or "").strip(),
                    (dados.get("comprimento") or "").strip(),
                    (dados.get("diametro") or "").strip(),
                    (dados.get("rosca") or "").strip(),
                    (dados.get("material") or "").strip(),
                    (dados.get("cor") or "").strip(),
                    (dados.get("norma") or "").strip(),
                    _to_int(dados.get("validade_dias")),
                    _to_int(dados.get("garantia_dias")),
                ),
            )
            produto_id = cur.lastrowid
            grupo_cod, subgrupo_cod, familia_cod = _contexto_sku(
                conn, grupo_id, subgrupo_id, familia_id, produto_id
            )
            sku, _aviso = reservar_sku(
                dados.get("sku") or "", produto_id,
                base=nome, ignorar_id=produto_id, conn=conn,
                grupo_cod=grupo_cod,
                subgrupo_cod=subgrupo_cod,
                familia_cod=familia_cod,
            )
            if sku:
                conn.execute("UPDATE produtos_cadastro SET sku=? WHERE id=?", (sku, produto_id))
            return produto_id

    def update_product(
        self,
        produto_id: int,
        familia_id: int | None,
        nome: str,
        marca: str,
        descricao: str,
        categoria: str,
        subcategoria: str = "",
        termos_busca: str = "",
        external_id: str | None = None,
        grupo_id: int | None = None,
        subgrupo_id: int | None = None,
        dados: dict | None = None,
        atributos: dict | None = None,
    ) -> tuple[bool, dict]:
        dados = dados or {}
        atributos = atributos or {}
        with system_conn() as conn:
            categoria_id, subcategoria_id = categorias.resolve(
                conn, categoria, subcategoria, subgrupo_id
            )
            grupo_id, subgrupo_id, categoria_id, subcategoria_id = categorias.validar_hierarquia(
                conn, grupo_id, subgrupo_id, categoria_id, subcategoria_id
            )
            marca_id = marcas.resolver(conn, marca)
            novo_sku = dados.get("sku") or ""
            if novo_sku:
                atual = conn.execute(
                    "SELECT sku FROM produtos_cadastro WHERE id=?", (produto_id,)
                ).fetchone()
                sku_atual = atual["sku"] if atual else ""
                if sku_atual and sku_emitido_variante(conn, produto_id) and \
                        normalizar_sku(novo_sku) != normalizar_sku(sku_atual):
                    novo_sku = sku_atual
            grupo_cod_sku, subgrupo_cod_sku, familia_cod_sku = _contexto_sku(
                conn, grupo_id, subgrupo_id, familia_id, produto_id
            )
            sku, _aviso = reservar_sku(
                novo_sku, produto_id,
                base=nome, ignorar_id=produto_id, conn=conn,
                grupo_cod=grupo_cod_sku,
                subgrupo_cod=subgrupo_cod_sku,
                familia_cod=familia_cod_sku,
            )
            cur = conn.execute(
                "UPDATE produtos_cadastro SET familia_id=?, nome=?, marca=?, marca_id=?, descricao=?,"
                " termos_busca=?, categoria_id=?, subcategoria_id=?, external_id=?, grupo_id=?, subgrupo_id=?,"
                " sku=?, ean=?, preco=?, preco_promocional=?, old_price=?, pix_price=?, custo_unitario=?, preco_venda=?,"
                " ncm=COALESCE(NULLIF(?, ''), ncm), peso=?, dimensoes=?, unidade_venda=?, embalagem=?,"
                " fator_conversao=?, localizacao=?, unidade_tributavel=?, atributos=?,"
                " bitola=?, tensao=?, potencia=?, comprimento=?, diametro=?, rosca=?, material=?, cor=?, norma=?,"
                " validade_dias=?, garantia_dias=?,"
                " atualizado_em=datetime('now') WHERE id=?",
                (
                    familia_id,
                    nome,
                    marca or "",
                    marca_id,
                    descricao or "",
                    termos_busca or "",
                    categoria_id,
                    subcategoria_id,
                    str(external_id).strip() if external_id else None,
                    grupo_id,
                    subgrupo_id,
                    sku,
                    dados.get("ean") or "",
                    _to_float(dados.get("preco")) or 0,
                    _to_float(dados.get("preco_promocional")),
                    _to_float(dados.get("old_price")),
                    _to_float(dados.get("pix_price")),
                    _to_float(dados.get("custo_unitario")),
                    _to_float(dados.get("preco_venda")),
                    (dados.get("ncm") or "").strip(),
                    _to_float(dados.get("peso")) or 0,
                    dados.get("dimensoes") or "",
                    (dados.get("unidade_venda") or "UN").strip(),
                    _to_float(dados.get("embalagem")) or 1,
                    _to_float(dados.get("fator_conversao")) or 1,
                    dados.get("localizacao") or "",
                    (dados.get("unidade_tributavel") or "").strip(),
                    json.dumps({str(k): str(v) for k, v in atributos.items() if v not in (None, "")}, ensure_ascii=False),
                    (dados.get("bitola") or "").strip(),
                    (dados.get("tensao") or "").strip(),
                    (dados.get("potencia") or "").strip(),
                    (dados.get("comprimento") or "").strip(),
                    (dados.get("diametro") or "").strip(),
                    (dados.get("rosca") or "").strip(),
                    (dados.get("material") or "").strip(),
                    (dados.get("cor") or "").strip(),
                    (dados.get("norma") or "").strip(),
                    _to_int(dados.get("validade_dias")),
                    _to_int(dados.get("garantia_dias")),
                    produto_id,
                ),
            )
            if cur.rowcount == 0:
                return False, {}
            return True, {"criadas": 0, "desativadas": 0, "excluidas": 0, "bloqueadas": 0, "atributos_faltantes": 0}

    def delete_product(self, produto_id: int) -> tuple[bool, dict]:
        """Exclui (soft) um produto. Como cada produto é uma unidade independente
        (não há variantes filhas), a exclusão é sempre uma desativação, preservando
        histórico e referências de estoque/preço/fornecedores."""
        with system_conn() as conn:
            cur = conn.execute(
                "UPDATE produtos_cadastro SET ativo=0, status_cadastro='bloqueado',"
                " atualizado_em=NOW() WHERE id=?",
                (produto_id,),
            )
            if cur.rowcount == 0:
                return False, {}
            return True, {"desativadas": 1, "excluidas": 0}

    # ------------------------------------------------------------------
    # Imagens
    # ------------------------------------------------------------------

    def add_imagem(
        self,
        produto_id: int,
        filename: str,
    ) -> int:
        with system_conn() as conn:
            conn.execute(
                "SELECT id FROM produtos_cadastro WHERE id=? FOR UPDATE",
                (produto_id,),
            )
            row = conn.execute(
                "SELECT COALESCE(MAX(ordem), -1) + 1 AS n FROM imagens_produto WHERE produto_id=?",
                (produto_id,),
            ).fetchone()
            cur = conn.execute(
                "INSERT INTO imagens_produto (produto_id, filename, ordem)"
                " VALUES (?,?,?)",
                (produto_id, filename, row["n"]),
            )
            return cur.lastrowid

    def add_imagens(self, produto_id: int, filenames: list[str]) -> list[int]:
        """Registra varias imagens em uma unica transacao e preserva a ordem."""
        if not filenames:
            return []
        with system_conn() as conn:
            conn.execute(
                "SELECT id FROM produtos_cadastro WHERE id=? FOR UPDATE",
                (produto_id,),
            )
            row = conn.execute(
                "SELECT COALESCE(MAX(ordem), -1) + 1 AS n FROM imagens_produto WHERE produto_id=?",
                (produto_id,),
            ).fetchone()
            first_order = int(row["n"])
            ids: list[int] = []
            for offset, filename in enumerate(filenames):
                cur = conn.execute(
                    "INSERT INTO imagens_produto (produto_id, filename, ordem) VALUES (?,?,?)",
                    (produto_id, filename, first_order + offset),
                )
                ids.append(int(cur.lastrowid))
            return ids

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
    # Fornecedor x Produto (códigos, unidade de compra, fator de conversão)
    # ------------------------------------------------------------------

    def get_fornecedor_variantes(self, conn, produto_id: int | None) -> list[dict]:
        """Mapeamentos fornecedor x produto (nome mantido por compatibilidade)."""
        if produto_id is None:
            return []
        rows = conn.execute(
            "SELECT fv.produto_id, fv.fornecedor_id, fv.codigo_fornecedor,"
            " fv.descricao_fornecedor, fv.unidade_compra, fv.fator_conversao,"
            " s.nome AS fornecedor_nome, p.sku"
            " FROM fornecedor_variantes fv"
            " JOIN fornecedores s ON s.id=fv.fornecedor_id"
            " JOIN produtos_cadastro p ON p.id=fv.produto_id"
            " WHERE fv.produto_id=?"
            " ORDER BY s.nome, fv.produto_id",
            (produto_id,),
        ).fetchall()
        return [dict(r) for r in rows]

    def save_fornecedor_variantes(
        self, conn, fornecedor_id: int, produto_id: int, itens: list[dict]
    ) -> int:
        """Substitui os mapeamentos de um fornecedor para um produto."""
        conn.execute(
            "DELETE FROM fornecedor_variantes WHERE fornecedor_id=? AND produto_id=?",
            (fornecedor_id, produto_id),
        )
        count = 0
        for item in itens or []:
            if item.get("produto_id") not in (None, produto_id):
                continue
            codigo = str(item.get("codigo_fornecedor") or "").strip()
            unidade = str(item.get("unidade_compra") or "").strip()
            fator = _to_float(item.get("fator_conversao"))
            conn.execute(
                "INSERT INTO fornecedor_variantes (produto_id, fornecedor_id,"
                " codigo_fornecedor, descricao_fornecedor, unidade_compra, fator_conversao)"
                " VALUES (?,?,?,?,?,?)"
                " ON CONFLICT(produto_id, fornecedor_id) DO UPDATE SET"
                " codigo_fornecedor=excluded.codigo_fornecedor,"
                " descricao_fornecedor=excluded.descricao_fornecedor,"
                " unidade_compra=excluded.unidade_compra,"
                " fator_conversao=excluded.fator_conversao",
                (
                    produto_id,
                    fornecedor_id,
                    codigo,
                    str(item.get("descricao_fornecedor") or "").strip(),
                    unidade,
                    fator if fator is not None else 1,
                ),
            )
            count += 1
        return count
