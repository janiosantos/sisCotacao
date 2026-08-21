"""Migração 0059 — Garantia: todo produto base possui ao menos uma variante.

Regra de negócio: cada `produtos_cadastro` deve ter pelo menos uma variante.
Cria uma **variante padrão** (preço 0, sem atributos, SKU `SKU-<produto>-<id>`)
para todo produto que ainda não possui nenhuma variante, e sincroniza o índice
de busca (`produtos_fts`).
"""
from __future__ import annotations

VERSION = 59
NAME = "garantir_variante_produto"


def guard(conn) -> bool:
    """Já garantida quando não existe produto sem variante."""
    row = conn.execute(
        "SELECT 1 FROM produtos_cadastro p"
        " WHERE NOT EXISTS (SELECT 1 FROM variantes v WHERE v.produto_id = p.id)"
        " LIMIT 1"
    ).fetchone()
    return row is None


def forward(conn) -> None:
    autocommit = conn.autocommit
    conn.autocommit = True
    try:
        rows = conn.execute(
            "SELECT p.id, COALESCE(p.marca,'') AS marca, p.familia_id"
            " FROM produtos_cadastro p"
            " WHERE NOT EXISTS (SELECT 1 FROM variantes v WHERE v.produto_id = p.id)"
        ).fetchall()
        ids = [r[0] for r in rows]
        for r in rows:
            produto_id, marca, familia_id = r[0], r[1], r[2]
            unidade = "UN"
            ncm = ""
            if familia_id:
                fr = conn.execute(
                    "SELECT COALESCE(ncm_padrao,'') AS ncm_padrao,"
                    " COALESCE(unidade_padrao,'UN') AS unidade_padrao"
                    " FROM familias WHERE id = %s",
                    (familia_id,),
                ).fetchone()
                if fr:
                    unidade = (fr[1] or "UN").strip() or "UN"
                    ncm = (fr[0] or "").strip()
            cur = conn.execute(
                "INSERT INTO variantes"
                " (produto_id, sku, ean, preco, preco_promocional, marca, observacao, ativo,"
                "  unidade_venda, embalagem, fator_conversao, unidade_tributavel, ncm, localizacao, atributos)"
                " VALUES (%s, '', '', 0, NULL, %s, '', 1, %s, 1, 1, '', %s, '', '{}'::jsonb)"
                " RETURNING id",
                (produto_id, marca, unidade, ncm),
            )
            vid = cur.fetchone()[0]
            conn.execute(
                "UPDATE variantes SET sku = %s WHERE id = %s",
                (f"SKU-{produto_id}-{vid}", vid),
            )
        if ids:
            conn.execute(
                """
                INSERT INTO produtos_fts (produto_id, nome, marca, descricao, familia, skus, termos_busca)
                SELECT p.id,
                       COALESCE(p.nome, ''),
                       COALESCE(p.marca, ''),
                       COALESCE(substr(COALESCE(p.descricao, ''), 1, 300), ''),
                       COALESCE(f.nome, ''),
                       COALESCE((
                           SELECT string_agg(tok, ' ')
                           FROM (
                               SELECT v.sku AS tok FROM variantes v
                               WHERE v.produto_id = p.id AND v.ativo = 1 AND v.sku <> ''
                               UNION
                               SELECT v.ean FROM variantes v
                               WHERE v.produto_id = p.id AND v.ativo = 1 AND v.ean <> ''
                           ) x
                       ), ''),
                       COALESCE(p.termos_busca, '')
                FROM produtos_cadastro p
                LEFT JOIN familias f ON f.id = p.familia_id
                WHERE p.id = ANY(%s)
                """,
                (ids,),
            )
    finally:
        conn.autocommit = autocommit


def backward(conn) -> None:
    autocommit = conn.autocommit
    conn.autocommit = True
    try:
        # Remove as variantes padrão criadas por esta migração (SKU-<produto>-<id>).
        conn.execute(
            "DELETE FROM variantes WHERE sku ~ '^SKU-[0-9]+-[0-9]+$'"
            " AND atributos = '{}'::jsonb AND preco = 0"
        )
    finally:
        conn.autocommit = autocommit
