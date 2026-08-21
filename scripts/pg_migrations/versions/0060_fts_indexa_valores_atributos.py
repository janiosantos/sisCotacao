"""Migração 0060 — Indexa valores de atributos na busca full-text.

Recria `produtos_fts` adicionando a coluna `atributos` (texto com os VALORES
dos atributos das variantes, sem os nomes) e incluindo-a no tsvector. Assim a
busca passa a encontrar produtos pelo valor de atributo (ex.: "verde",
"2,5mm") — não pelo nome do atributo.
"""
from __future__ import annotations

VERSION = 60
NAME = "fts_indexa_valores_atributos"
RISCO = "critica"

# DDL recriada com a coluna `atributos` no tsvector (espelho de fts.py).
_FTS_DDL = """
CREATE TABLE IF NOT EXISTS produtos_fts (
    produto_id BIGINT PRIMARY KEY,
    nome TEXT NOT NULL DEFAULT '',
    marca TEXT NOT NULL DEFAULT '',
    descricao TEXT NOT NULL DEFAULT '',
    familia TEXT NOT NULL DEFAULT '',
    skus TEXT NOT NULL DEFAULT '',
    termos_busca TEXT NOT NULL DEFAULT '',
    atributos TEXT NOT NULL DEFAULT '',
    fts tsvector GENERATED ALWAYS AS (
        to_tsvector('simple', public.f_unaccent(
            coalesce(nome, '') || ' ' || coalesce(marca, '') || ' ' ||
            coalesce(descricao, '') || ' ' || coalesce(familia, '') || ' ' ||
            coalesce(skus, '') || ' ' || coalesce(termos_busca, '') || ' ' ||
            coalesce(atributos, '')
        ))
    ) STORED
);
"""

_FTS_SELECT = """
SELECT p.id AS id,
       COALESCE(p.nome, '') AS nome,
       COALESCE(p.marca, '') AS marca,
       COALESCE(substr(COALESCE(p.descricao, ''), 1, 300), '') AS descricao,
       COALESCE(f.nome, '') AS familia,
       COALESCE((
           SELECT string_agg(tok, ' ')
           FROM (
               SELECT v.sku AS tok FROM variantes v
               WHERE v.produto_id = p.id AND v.ativo = 1 AND v.sku <> ''
               UNION
               SELECT v.ean FROM variantes v
               WHERE v.produto_id = p.id AND v.ativo = 1 AND v.ean <> ''
           ) x
       ), '') AS skus,
       COALESCE(p.termos_busca, '') AS termos_busca,
       COALESCE((
           SELECT string_agg(kv.value, ' ')
           FROM variantes v, jsonb_each_text(v.atributos) kv(key, value)
           WHERE v.produto_id = p.id AND v.ativo = 1 AND kv.value <> ''
       ), '') AS atributos
FROM produtos_cadastro p
LEFT JOIN familias f ON f.id = p.familia_id
"""


def guard(conn) -> bool:
    row = conn.execute(
        "SELECT 1 FROM information_schema.columns"
        " WHERE table_name='produtos_fts' AND column_name='atributos'"
    ).fetchone()
    return row is not None


def forward(conn) -> None:
    autocommit = conn.autocommit
    conn.autocommit = True
    try:
        conn.execute("DROP TABLE IF EXISTS produtos_fts")
        conn.execute(_FTS_DDL)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_produtos_fts_fts ON produtos_fts USING gin (fts)")
        conn.execute(
            "INSERT INTO produtos_fts (produto_id, nome, marca, descricao, familia, skus, termos_busca, atributos)"
            f" {_FTS_SELECT}"
        )
    finally:
        conn.autocommit = autocommit


def backward(conn) -> None:
    autocommit = conn.autocommit
    conn.autocommit = True
    try:
        conn.execute("DROP TABLE IF EXISTS produtos_fts")
        conn.execute("""
            CREATE TABLE IF NOT EXISTS produtos_fts (
                produto_id BIGINT PRIMARY KEY,
                nome TEXT NOT NULL DEFAULT '',
                marca TEXT NOT NULL DEFAULT '',
                descricao TEXT NOT NULL DEFAULT '',
                familia TEXT NOT NULL DEFAULT '',
                skus TEXT NOT NULL DEFAULT '',
                termos_busca TEXT NOT NULL DEFAULT '',
                fts tsvector GENERATED ALWAYS AS (
                    to_tsvector('simple', public.f_unaccent(
                        coalesce(nome, '') || ' ' || coalesce(marca, '') || ' ' ||
                        coalesce(descricao, '') || ' ' || coalesce(familia, '') || ' ' ||
                        coalesce(skus, '') || ' ' || coalesce(termos_busca, '')
                    ))
                ) STORED
            );
        """)
    finally:
        conn.autocommit = autocommit
