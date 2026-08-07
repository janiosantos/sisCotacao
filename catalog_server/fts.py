"""Índice de texto completo (FTS5) para a busca rápida de produtos.

A busca antiga usava `LIKE '%termo%'` com varredura completa da tabela — com
dezenas de milhares de produtos ficou lenta. O FTS5 indexa nome, marca,
descrição, família e os SKU/EAN das variações, permitindo busca por prefixo,
insensível a acentos (`unicode61 remove_diacritics 2`).

O índice é mantido:
- em lote no startup do servidor (`rebuild`, após a sincronização do scraper);
- incrementalmente em cada escrita de produto (CRUD manual e importação por URL).
"""
from __future__ import annotations

import re

_FTS = "produtos_fts"

_CREATE = f"""
CREATE VIRTUAL TABLE IF NOT EXISTS {_FTS} USING fts5(
    produto_id UNINDEXED,
    nome,
    marca,
    descricao,
    familia,
    skus,
    termos_busca,
    tokenize='unicode61 remove_diacritics 2'
)
"""

# O que vai para o índice, por produto.
_SELECT_FOR_INDEX = """
SELECT p.id AS id,
       COALESCE(p.nome, '') AS nome,
       COALESCE(p.marca, '') AS marca,
       COALESCE(substr(COALESCE(p.descricao, ''), 1, 300), '') AS descricao,
       COALESCE(f.nome, '') AS familia,
       COALESCE((
           SELECT group_concat(tok, ' ')
           FROM (
               SELECT v.sku AS tok FROM variantes v
               WHERE v.produto_id = p.id AND v.ativo = 1 AND v.sku <> ''
               UNION
               SELECT v.ean FROM variantes v
               WHERE v.produto_id = p.id AND v.ativo = 1 AND v.ean <> ''
           )
       ), '') AS skus,
       COALESCE(p.termos_busca, '') AS termos_busca
FROM produtos_cadastro p
LEFT JOIN familias f ON f.id = p.familia_id
"""

_QUERY_TOKENS = re.compile(r"[0-9A-Za-z\u00C0-\u00D6\u00D8-\u00F6\u00F8-\u00FF]+")


def ensure_fts(conn) -> None:
    """Garante que a tabela virtual FTS exista (idempotente)."""
    conn.execute(_CREATE)


def is_empty(conn) -> bool:
    row = conn.execute(f"SELECT COUNT(*) AS n FROM {_FTS}").fetchone()
    return not row or not row[0]


def rebuild(conn) -> None:
    """Reconstrói o índice a partir das tabelas base."""
    conn.execute(f"DELETE FROM {_FTS}")
    conn.execute(
        f"INSERT INTO {_FTS}(produto_id, nome, marca, descricao, familia, skus, termos_busca)"
        f" {_SELECT_FOR_INDEX}"
    )


def sync_product(conn, produto_id: int) -> None:
    """Atualiza o índice para um único produto (create-or-replace)."""
    conn.execute(f"DELETE FROM {_FTS} WHERE produto_id = ?", (produto_id,))
    row = conn.execute(
        f"{_SELECT_FOR_INDEX} WHERE p.id = ?", (produto_id,)
    ).fetchone()
    if row is not None and row["id"] is not None:
        conn.execute(
            f"INSERT INTO {_FTS}(produto_id, nome, marca, descricao, familia, skus, termos_busca)"
            " VALUES (?,?,?,?,?,?,?)",
            (
                row["id"], row["nome"], row["marca"], row["descricao"],
                row["familia"], row["skus"], row["termos_busca"],
            ),
        )


def delete_product(conn, produto_id: int) -> None:
    conn.execute(f"DELETE FROM {_FTS} WHERE produto_id = ?", (produto_id,))


def search_query(q: str) -> str:
    """Converte o termo livre em uma query FTS5 com prefixo por token.

    Ex.: "parafuso 5x50" -> `parafuso* AND 5x50*`.
    Retorna string vazia se não houver tokens utilizáveis.
    """
    tokens = _QUERY_TOKENS.findall(q)
    return " AND ".join(f"{tok}*" for tok in tokens)
