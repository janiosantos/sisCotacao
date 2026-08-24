"""Migração 0080 — Portal de compras do fornecedor rico (v2.20.0).

Expande a resposta do representante no portal público de cotações:

- `cotacao_precos.unidade_compra`: unidade ofertada pelo fornecedor
  (UN/CX/MT/KG…), sugerida da variante mas editável.
- `cotacao_precos.fator_conversao`: quantos por embalagem (ex.: caixa com 12).
- `cotacao_precos.marca_ofertada`: marca que o fornecedor está cotando.
- `cotacao_precos.motivo_indisponibilidade`: em_falta_estoque |
  nao_trabalha_linha | descontinuado | fora_regiao | outro (vazio = disponível).
- `cotacao_itens.unidade_solicitada`: snapshot da unidade da variante no
  momento da cotação (para o portal/pedido).

Sem remoção de estrutura: `disponibilidade_estoque` continua (compat).
"""
from __future__ import annotations

VERSION = 80
RISCO = "moderada"
NAME = "compras_portal"

MUDANCA = {
    "o_que": [
        "cotacao_precos: colunas unidade_compra, fator_conversao, marca_ofertada e motivo_indisponibilidade",
        "cotacao_itens: coluna unidade_solicitada (snapshot da unidade da variante)",
        "Sem mudança destrutiva: disponibilidade_estoque continua como está (compat)",
    ],
    "porque": [
        "Representante precisa responder online com unidade/embalagem, marca ofertada e motivo de indisponibilidade (referências TOTVS/MRV)",
        "O comprador da Casa LM precisa comparar propostas por embalagem e conferir a unidade no pedido",
    ],
}


def guard(conn) -> bool:
    row = conn.execute(
        "SELECT 1 FROM information_schema.columns"
        " WHERE table_name='cotacao_precos' AND column_name='unidade_compra'"
    ).fetchone()
    return row is not None


def forward(conn) -> None:
    ac = conn.autocommit
    conn.autocommit = True
    try:
        conn.execute(
            "ALTER TABLE cotacao_precos"
            " ADD COLUMN IF NOT EXISTS unidade_compra TEXT DEFAULT ''"
        )
        conn.execute(
            "ALTER TABLE cotacao_precos"
            " ADD COLUMN IF NOT EXISTS fator_conversao NUMERIC(10,3) NOT NULL DEFAULT 1"
        )
        conn.execute(
            "ALTER TABLE cotacao_precos"
            " ADD COLUMN IF NOT EXISTS marca_ofertada TEXT DEFAULT ''"
        )
        conn.execute(
            "ALTER TABLE cotacao_precos"
            " ADD COLUMN IF NOT EXISTS motivo_indisponibilidade TEXT DEFAULT ''"
        )
        conn.execute(
            "ALTER TABLE cotacao_itens"
            " ADD COLUMN IF NOT EXISTS unidade_solicitada TEXT DEFAULT ''"
        )
    finally:
        conn.autocommit = ac


def backward(conn) -> None:
    ac = conn.autocommit
    conn.autocommit = True
    try:
        conn.execute("ALTER TABLE cotacao_itens DROP COLUMN IF EXISTS unidade_solicitada")
        conn.execute("ALTER TABLE cotacao_precos DROP COLUMN IF EXISTS motivo_indisponibilidade")
        conn.execute("ALTER TABLE cotacao_precos DROP COLUMN IF EXISTS marca_ofertada")
        conn.execute("ALTER TABLE cotacao_precos DROP COLUMN IF EXISTS fator_conversao")
        conn.execute("ALTER TABLE cotacao_precos DROP COLUMN IF EXISTS unidade_compra")
    finally:
        conn.autocommit = ac