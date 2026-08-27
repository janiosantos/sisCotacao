"""Migração 0086 — Unificação produto/variante (Migrate, v2.26.0).

Passo Migrate do plano de simplificação: cada variante passa a ser um produto
independente. Cria:

- `variante_produto_map`: mapeia cada `variantes.id` para o `produtos_cadastro.id`
  destino (a variante principal de cada card já é o próprio produto; as variantes
  extras viram produtos novos, réplicas dos metadados do card + dados da variante).
- Os produtos novos para as variantes extras (~3.048).
- Índice de apoio.

NÃO reaponta as tabelas de negócio ainda (isso é a etapa seguinte, 0087, após
validação). Esta migração só materializa o mapa e os produtos independentes,
mantendo o sistema funcional (nada é removido nem alterado nas tabelas atuais).

Expand/Migrate em fases — Contract (drop de `variantes`) fica para o final.
"""
from __future__ import annotations

VERSION = 86
RISCO = "critica"
NAME = "produto_unificado_migrate"

MUDANCA = {
    "o_que": [
        "Cria tabela variante_produto_map (variante_id -> produto_id destino)",
        "Cria produtos independentes para as variantes extras (réplica do card + dados da variante)",
        "Preenche o mapa: variante principal → produto existente; variantes extras → produto novo",
        "Índice em variante_produto_map (variante_id)",
    ],
    "porque": [
        "Cada variante vira um produto independente (modelo simplificado)",
        "O mapa é a base para reapontar as ~23 tabelas de negócio na etapa seguinte",
        "Migrate do plano Expand→Migrate→Contract, sem tocar nas tabelas atuais (sistema segue funcional)",
    ],
}


def guard(conn) -> bool:
    row = conn.execute(
        "SELECT 1 FROM information_schema.tables"
        " WHERE table_schema='public' AND table_name='variante_produto_map'"
    ).fetchone()
    return row is not None


def forward(conn) -> None:
    ac = conn.autocommit
    conn.autocommit = True
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS variante_produto_map (
                variante_id  BIGINT PRIMARY KEY,
                produto_id   BIGINT NOT NULL
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_vpm_produto ON variante_produto_map (produto_id)"
        )

        # 1) Variante principal de cada card -> o próprio produto (id do card).
        #    A principal é a de menor id ativa; se não houver ativa, menor id.
        conn.execute(
            """
            INSERT INTO variante_produto_map (variante_id, produto_id)
            SELECT DISTINCT ON (v.produto_id) v.id, v.produto_id
            FROM variantes v
            ORDER BY v.produto_id, v.ativo DESC, v.id
            """
        )

        # 2) Cria produtos independentes para as variantes extras.
        #    Herda os metadados do card e os dados operacionais da variante.
        conn.execute(
            """
            INSERT INTO produtos_cadastro
              (familia_id, nome, marca, marca_id, descricao, termos_busca,
               categoria_id, subcategoria_id, external_id, grupo_id, subgrupo_id,
               em_linha, sku, ean, preco, preco_promocional, old_price, pix_price,
               installment, custo_unitario, preco_venda, ncm, peso, dimensoes,
               unidade_venda, embalagem, fator_conversao, localizacao,
               unidade_tributavel)
            SELECT
              p.familia_id, p.nome, v.marca, p.marca_id, p.descricao, p.termos_busca,
              p.categoria_id, p.subcategoria_id, v.external_id, p.grupo_id, p.subgrupo_id,
              p.em_linha, v.sku, v.ean, v.preco, v.preco_promocional, v.old_price,
              v.pix_price, v.installment, v.custo_unitario, v.preco_venda, v.ncm,
              v.peso, v.dimensoes, v.unidade_venda, v.embalagem, v.fator_conversao,
              v.localizacao, v.unidade_tributavel
            FROM variantes v
            JOIN produtos_cadastro p ON p.id = v.produto_id
            WHERE v.id NOT IN (SELECT variante_id FROM variante_produto_map)
            """
        )

        # 3) Associa as variantes extras ao produto novo criado (o último insert).
        #    Como não há como mapear direto por nome único, associamos pela ordem:
        #    para cada variante extra, o produto novo é o que foi criado agora com
        #    o mesmo sku/ean (único por variante).
        conn.execute(
            """
            INSERT INTO variante_produto_map (variante_id, produto_id)
            SELECT v.id, np.id
            FROM variantes v
            JOIN produtos_cadastro np ON np.sku = v.sku AND np.ean IS NOT DISTINCT FROM v.ean
            WHERE v.id NOT IN (SELECT variante_id FROM variante_produto_map)
              AND np.id NOT IN (SELECT produto_id FROM variante_produto_map)
            """
        )

        # 4) Segurança: se ainda restarem variantes sem mapa (sku duplicado/ausente),
        #    associa ao produto principal do card (fallback) para não perder referência.
        conn.execute(
            """
            INSERT INTO variante_produto_map (variante_id, produto_id)
            SELECT v.id, v.produto_id
            FROM variantes v
            WHERE v.id NOT IN (SELECT variante_id FROM variante_produto_map)
            """
        )
    finally:
        conn.autocommit = ac


def backward(conn) -> None:
    ac = conn.autocommit
    conn.autocommit = True
    try:
        conn.execute("DROP INDEX IF EXISTS idx_vpm_produto")
        conn.execute("DROP TABLE IF EXISTS variante_produto_map")
    finally:
        conn.autocommit = ac