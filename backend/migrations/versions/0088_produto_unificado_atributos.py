"""Migração 0088 — Unificação produto/variante (Atributos, v2.26.0).

Passo Migrate do plano de simplificação: cada produto corresponde agora a uma
antiga variante. Os valores de atributos (tamanho/cor/etc.) que pertenciam à
variante viviam no EAV `variante_atributos` (coluna `variante_id`, apontando
para o id da variante original). Esta migração move esses valores para o JSONB
`produtos_cadastro.atributos`, chaveado por nome do atributo (fonte canônica,
espelhando o antigo `variantes.atributos`).

O deslocamento usa `variante_produto_map` (variante original -> produto
destino), criado na 0086. O EAV `variante_atributos` e a tabela de apoio
`variante_produto_map` serão eliminados no Contract — daqui em diante o app só
lê `produtos_cadastro.atributos`.

Idempotente e reversível (o EAV não é removido).
"""
from __future__ import annotations

VERSION = 88
RISCO = "critica"
NAME = "produto_unificado_atributos"

MUDANCA = {
    "o_que": [
        "Adiciona coluna JSONB produtos_cadastro.atributos",
        "Backfill dos valores do EAV variante_atributos (via variante_produto_map) para produtos_cadastro.atributos, chaveado por nome do atributo",
        "Índice GIN em produtos_cadastro.atributos (busca por atributo)",
    ],
    "porque": [
        "Cada produto agora é uma antiga variante; seus atributos devem morar no próprio produto",
        "variante_atributos/variante_produto_map serão eliminados no Contract",
        "Migrate do plano Expand→Migrate→Contract",
    ],
}


def guard(conn) -> bool:
    row = conn.execute(
        "SELECT 1 FROM information_schema.columns"
        " WHERE table_schema='public' AND table_name='produtos_cadastro'"
        "   AND column_name='atributos'"
    ).fetchone()
    return row is not None


def forward(conn) -> None:
    ac = conn.autocommit
    conn.autocommit = True
    try:
        conn.execute(
            "ALTER TABLE produtos_cadastro ADD COLUMN IF NOT EXISTS atributos JSONB"
        )
        conn.execute(
            """
            UPDATE produtos_cadastro p
            SET atributos = sub.j
            FROM (
                SELECT vpm.produto_id AS pid,
                       jsonb_object_agg(
                           COALESCE(fa.nome, va.atributo_id::text),
                           va.valor
                       ) AS j
                FROM variante_atributos va
                JOIN variante_produto_map vpm ON vpm.variante_id = va.variante_id
                LEFT JOIN familia_atributos fa ON fa.id = va.atributo_id
                GROUP BY vpm.produto_id
            ) sub
            WHERE p.id = sub.pid
              AND p.atributos IS NULL
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_produtos_atributos"
            " ON produtos_cadastro USING GIN (atributos)"
        )
    finally:
        conn.autocommit = ac


def backward(conn) -> None:
    ac = conn.autocommit
    conn.autocommit = True
    try:
        conn.execute("DROP INDEX IF EXISTS idx_produtos_atributos")
        conn.execute(
            "ALTER TABLE produtos_cadastro DROP COLUMN IF EXISTS atributos"
        )
    finally:
        conn.autocommit = ac
