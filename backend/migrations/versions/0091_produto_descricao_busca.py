"""Migração 0091 — Descrição padronizada + busca sem produtos_fts (v2.26.3).

Substitui o índice de texto completo (`produtos_fts`) por busca ILIKE +
`pg_trgm` sobre colunas de `produtos_cadastro` com a **descrição padronizada**:

- `descricao` passa a ser a etiqueta padrão: `<Nome> + <valores dos atributos
  da família, na ordem> + " - " + <Marca>` (ex.: "Cabo Flexível 2,5mm² Verde
  750V - SIL"). Backfill idempotente (determinístico).
- `DROP` de `produtos_fts` e da função `fts5_to_tsquery` (Contract).
- Índices GIN `pg_trgm` sobre `f_unaccent(nome|marca|sku|ean|termos_busca|descricao)`
  para ILIKE insensível a acentos e rápido.

`unaccent`, `pg_trgm` e `f_unaccent` permanecem (usados pela nova busca).
"""
from __future__ import annotations

VERSION = 91
RISCO = "critica"
NAME = "produto_descricao_busca"

MUDANCA = {
    "o_que": [
        "Backfill da descricao padronizada: Nome + atributos (ordem da família) + Marca",
        "DROP da tabela produtos_fts e da função fts5_to_tsquery",
        "Índices GIN pg_trgm em f_unaccent(nome, marca, sku, ean, termos_busca, descricao)",
    ],
    "porque": [
        "A busca por descrição padronizada (com características embutidas) é mais precisa que o FTS",
        "o FTS casava termos dentro do texto cru do scraper (ruído, ex.: 'fixação de cabos')",
        "Contract do plano de simplificação da busca",
    ],
}


def guard(conn) -> bool:
    row = conn.execute(
        "SELECT 1 FROM information_schema.tables"
        " WHERE table_schema='public' AND table_name='produtos_fts'"
    ).fetchone()
    return row is None


def forward(conn) -> None:
    ac = conn.autocommit
    conn.autocommit = True
    try:
        conn.execute("CREATE EXTENSION IF NOT EXISTS unaccent")
        conn.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
        conn.execute(
            """
            CREATE OR REPLACE FUNCTION f_unaccent(text) RETURNS text
            LANGUAGE sql IMMUTABLE PARALLEL SAFE AS $$
              SELECT public.unaccent('public.unaccent', $1)
            $$;
            """
        )

        # 1) Descrição padronizada — produtos com atributos (na ordem da família).
        conn.execute(
            """
            WITH attrs AS (
                SELECT p.id AS produto_id,
                       string_agg(kv.value, ' ' ORDER BY fa.ordem, fa.id) AS vals
                FROM produtos_cadastro p
                JOIN familia_atributos fa ON fa.familia_id = p.familia_id
                JOIN jsonb_each_text(p.atributos) kv ON kv.key = fa.nome
                WHERE kv.value <> ''
                GROUP BY p.id
            )
            UPDATE produtos_cadastro p
            SET descricao = btrim(
                coalesce(p.nome, '')
                || CASE WHEN a.vals IS NOT NULL AND a.vals <> ''
                        THEN ' ' || a.vals ELSE '' END
                || CASE WHEN btrim(coalesce(p.marca, '')) <> ''
                        THEN ' - ' || btrim(p.marca) ELSE '' END)
            FROM attrs a
            WHERE a.produto_id = p.id
            """
        )
        # 2) Produtos sem atributos (ou sem família) — descrição = Nome - Marca.
        conn.execute(
            """
            UPDATE produtos_cadastro p
            SET descricao = btrim(
                coalesce(p.nome, '')
                || CASE WHEN btrim(coalesce(p.marca, '')) <> ''
                        THEN ' - ' || btrim(p.marca) ELSE '' END)
            WHERE NOT EXISTS (
                SELECT 1
                FROM familia_atributos fa
                JOIN jsonb_each_text(p.atributos) kv ON kv.key = fa.nome
                WHERE fa.familia_id = p.familia_id AND kv.value <> ''
            )
            """
        )

        # 3) Contract do FTS.
        conn.execute("DROP TABLE IF EXISTS produtos_fts")
        conn.execute("DROP FUNCTION IF EXISTS fts5_to_tsquery(text)")

        # 4) Índices pg_trgm da nova busca.
        for col in ("nome", "marca", "sku", "ean", "termos_busca", "descricao"):
            conn.execute(
                f"CREATE INDEX IF NOT EXISTS idx_produtos_{col}_trgm"
                f" ON produtos_cadastro USING gin (f_unaccent({col}) gin_trgm_ops)"
            )
    finally:
        conn.autocommit = ac


def backward(conn) -> None:
    ac = conn.autocommit
    conn.autocommit = True
    try:
        for col in ("nome", "marca", "sku", "ean", "termos_busca", "descricao"):
            conn.execute(f"DROP INDEX IF EXISTS idx_produtos_{col}_trgm")
        # produtos_fts é recriado pela migração 0060 num banco vazio; a descricao
        # padronizada não é revertida (dados determinísticos; o FTS não dependia dela).
    finally:
        conn.autocommit = ac