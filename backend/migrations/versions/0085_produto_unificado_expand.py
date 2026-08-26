"""Migração 0085 — Unificação produto/variante (Expand, v2.26.0).

Passo Expand do plano de simplificação: cada variante passa a ser um produto
independente (a tabela `variantes` será eliminada no Contract final).

Adiciona a `produtos_cadastro` as colunas operacionais que hoje vivem na
`variantes` (SKU, preço, EAN, custo, NCM, peso, unidade, etc.), com índices
e backfill a partir da variante "principal" de cada produto.

Não remove nada (Expand-only). As tabelas com `variante_id` continuam a
apontar para `variantes` até o Contract — o sistema segue funcionando.
"""
from __future__ import annotations

VERSION = 85
RISCO = "critica"
NAME = "produto_unificado_expand"

MUDANCA = {
    "o_que": [
        "produtos_cadastro: adiciona colunas operacionais herdadas de variantes (sku, ean, preco, preco_promocional, custo_unitario, ncm, peso, dimensoes, unidade_venda, embalagem, fator_conversao, localizacao, pix_price, installment, external_id, marca, unidade_tributavel)",
        "Backfill: preenche essas colunas a partir da variante principal de cada produto (menor id ativo)",
        "Índices para busca por sku/ean em produtos_cadastro",
    ],
    "porque": [
        "Prepara o cadastro simplificado: cada produto passa a carregar seus próprios dados operacionais sem depender da tabela variantes",
        "Expand do plano Expand→Migrate→Contract (AGENTS.md regra de ouro)",
    ],
}


def guard(conn) -> bool:
    row = conn.execute(
        "SELECT 1 FROM information_schema.columns"
        " WHERE table_name='produtos_cadastro' AND column_name='sku'"
    ).fetchone()
    return row is not None


def forward(conn) -> None:
    ac = conn.autocommit
    conn.autocommit = True
    try:
        add = [
            ("sku", "TEXT"), ("ean", "TEXT"), ("preco", "DOUBLE PRECISION"),
            ("preco_promocional", "DOUBLE PRECISION"), ("old_price", "DOUBLE PRECISION"),
            ("pix_price", "DOUBLE PRECISION"), ("installment", "TEXT"),
            ("custo_unitario", "DOUBLE PRECISION"), ("preco_venda", "DOUBLE PRECISION"),
            ("ncm", "TEXT"), ("peso", "DOUBLE PRECISION"), ("dimensoes", "TEXT"),
            ("unidade_venda", "TEXT"), ("embalagem", "DOUBLE PRECISION"),
            ("fator_conversao", "DOUBLE PRECISION"), ("localizacao", "TEXT"),
            ("unidade_tributavel", "TEXT"), ("marca", "TEXT"),
        ]
        for col, tipo in add:
            conn.execute(
                f"ALTER TABLE produtos_cadastro ADD COLUMN IF NOT EXISTS {col} {tipo}"
            )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_produtos_cadastro_sku ON produtos_cadastro (sku)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_produtos_cadastro_ean ON produtos_cadastro (ean)"
        )
        # Backfill a partir da variante principal (menor id ativa) de cada produto.
        conn.execute(
            """
            UPDATE produtos_cadastro p SET
              sku = v.sku,
              ean = v.ean,
              preco = v.preco,
              preco_promocional = v.preco_promocional,
              old_price = v.old_price,
              pix_price = v.pix_price,
              installment = v.installment,
              custo_unitario = v.custo_unitario,
              preco_venda = v.preco_venda,
              ncm = v.ncm,
              peso = v.peso,
              dimensoes = v.dimensoes,
              unidade_venda = v.unidade_venda,
              embalagem = v.embalagem,
              fator_conversao = v.fator_conversao,
              localizacao = v.localizacao,
              unidade_tributavel = v.unidade_tributavel,
              marca = v.marca,
              external_id = COALESCE(p.external_id, v.external_id)
            FROM (
              SELECT DISTINCT ON (produto_id) produto_id, sku, ean, preco, preco_promocional,
                     old_price, pix_price, installment, custo_unitario, preco_venda, ncm,
                     peso, dimensoes, unidade_venda, embalagem, fator_conversao,
                     localizacao, unidade_tributavel, marca, external_id
              FROM variantes WHERE ativo=1 ORDER BY produto_id, id
            ) v
            WHERE v.produto_id = p.id
            """
        )
    finally:
        conn.autocommit = ac


def backward(conn) -> None:
    ac = conn.autocommit
    conn.autocommit = True
    try:
        conn.execute("DROP INDEX IF EXISTS idx_produtos_cadastro_ean")
        conn.execute("DROP INDEX IF EXISTS idx_produtos_cadastro_sku")
        cols = ["sku", "ean", "preco", "preco_promocional", "old_price", "pix_price",
                "installment", "custo_unitario", "preco_venda", "ncm", "peso", "dimensoes",
                "unidade_venda", "embalagem", "fator_conversao", "localizacao",
                "unidade_tributavel", "marca"]
        for col in cols:
            conn.execute(f"ALTER TABLE produtos_cadastro DROP COLUMN IF EXISTS {col}")
    finally:
        conn.autocommit = ac