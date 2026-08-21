"""Índice de texto completo (tsvector Postgres) para a busca rápida de produtos.

A busca antiga usava `LIKE '%termo%'` com varredura completa da tabela — com
dezenas de milhares de produtos ficou lenta. No Postgres, `produtos_fts` indexa
nome, marca, descrição, família e os SKU/EAN das variações em um `tsvector`
(GENERATED ALWAYS AS ... STORED) com busca por prefixo e insensível a acentos
(`unaccent` + parser `simple`).

O índice é mantido:
- em lote no startup do servidor (`rebuild`);
- incrementalmente em cada escrita de produto (CRUD manual e importação por URL).
"""
from __future__ import annotations

import re

_FTS = "produtos_fts"

# DDL do índice tsvector no Postgres (idempotente). `unaccent` é STABLE,
# então o wrapper IMMUTABLE `f_unaccent` permite usar em generated column.
_PG_CREATE = [
    "CREATE EXTENSION IF NOT EXISTS unaccent",
    "CREATE EXTENSION IF NOT EXISTS pg_trgm",
    """
CREATE OR REPLACE FUNCTION f_unaccent(text) RETURNS text
LANGUAGE sql IMMUTABLE PARALLEL SAFE AS $$
  SELECT public.unaccent('public.unaccent', $1)
$$;
""",
    """
CREATE OR REPLACE FUNCTION fts5_to_tsquery(q text) RETURNS tsquery
LANGUAGE sql IMMUTABLE PARALLEL SAFE AS $$
  SELECT to_tsquery('simple', string_agg(
    CASE WHEN tok LIKE '%*' THEN left(tok, -1) || ':*' ELSE tok END, ' & '))
  FROM regexp_split_to_table(lower(f_unaccent(coalesce(q, ''))), '\\s+and\\s+') tok
  WHERE tok <> ''
$$;
""",
    f"""
CREATE TABLE IF NOT EXISTS {_FTS} (
    produto_id BIGINT PRIMARY KEY,
    nome TEXT NOT NULL DEFAULT '',
    marca TEXT NOT NULL DEFAULT '',
    descricao TEXT NOT NULL DEFAULT '',
    familia TEXT NOT NULL DEFAULT '',
    skus TEXT NOT NULL DEFAULT '',
    termos_busca TEXT NOT NULL DEFAULT '',
    atributos TEXT NOT NULL DEFAULT '',
    fts tsvector GENERATED ALWAYS AS (
        to_tsvector('simple', f_unaccent(
            coalesce(nome, '') || ' ' || coalesce(marca, '') || ' ' ||
            coalesce(descricao, '') || ' ' || coalesce(familia, '') || ' ' ||
            coalesce(skus, '') || ' ' || coalesce(termos_busca, '') || ' ' ||
            coalesce(atributos, '')
        ))
    ) STORED
);
""",
    f"CREATE INDEX IF NOT EXISTS idx_produtos_fts_fts ON {_FTS} USING gin (fts)",
]

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
       COALESCE(p.termos_busca, '') AS termos_busca,
       COALESCE((
           SELECT group_concat(kv.value, ' ')
           FROM variantes v, jsonb_each_text(v.atributos) kv(key, value)
           WHERE v.produto_id = p.id AND v.ativo = 1 AND kv.value <> ''
       ), '') AS atributos
FROM produtos_cadastro p
LEFT JOIN familias f ON f.id = p.familia_id
"""

_QUERY_TOKENS = re.compile(r"[0-9A-Za-z\u00C0-\u00D6\u00D8-\u00F6\u00F8-\u00FF]+")


def ensure_fts(conn) -> None:
    """Garante que o índice FTS exista no Postgres (idempotente)."""
    row = conn.execute("SELECT to_regclass('public.produtos_fts') AS t").fetchone()
    if row is not None and row[0] is not None:
        return
    for stmt in _PG_CREATE:
        conn.execute(stmt)


def is_empty(conn) -> bool:
    ensure_fts(conn)
    row = conn.execute(f"SELECT COUNT(*) AS n FROM {_FTS}").fetchone()
    return not row or not row[0]


def rebuild(conn) -> None:
    """Reconstrói o índice a partir das tabelas base."""
    ensure_fts(conn)
    conn.execute(f"DELETE FROM {_FTS}")
    conn.execute(
        f"INSERT INTO {_FTS}(produto_id, nome, marca, descricao, familia, skus, termos_busca, atributos)"
        f" {_SELECT_FOR_INDEX}"
    )


def sync_product(conn, produto_id: int) -> None:
    """Atualiza o índice para um único produto (create-or-replace)."""
    ensure_fts(conn)
    conn.execute(f"DELETE FROM {_FTS} WHERE produto_id = ?", (produto_id,))
    row = conn.execute(
        f"{_SELECT_FOR_INDEX} WHERE p.id = ?", (produto_id,)
    ).fetchone()
    if row is not None and row["id"] is not None:
        conn.execute(
            f"INSERT INTO {_FTS}(produto_id, nome, marca, descricao, familia, skus, termos_busca, atributos)"
            " VALUES (?,?,?,?,?,?,?,?)",
            (
                row["id"], row["nome"], row["marca"], row["descricao"],
                row["familia"], row["skus"], row["termos_busca"], row["atributos"],
            ),
        )


def delete_product(conn, produto_id: int) -> None:
    ensure_fts(conn)
    conn.execute(f"DELETE FROM {_FTS} WHERE produto_id = ?", (produto_id,))


def search_query(q: str) -> str:
    """Converte o termo livre em uma query FTS com prefixo por token.

    Ex.: "parafuso 5x50" -> `parafuso* AND 5x50*`.
    Retorna string vazia se não houver tokens utilizáveis.
    """
    tokens = _QUERY_TOKENS.findall(q)
    return " AND ".join(f"{tok}*" for tok in tokens)