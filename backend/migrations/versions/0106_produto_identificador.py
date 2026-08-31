"""Migra��ǜo 0106 �?" identificadores m�ltiplos de produto (MDM-003)."""
from __future__ import annotations

VERSION = 106
RISCO = "baixa"  # Expand: tabela nova, sem alterar contrato existente
NAME = "produto_identificador"

MUDANCA = {
    "o_que": [
        "Cria tabela produto_identificador (EAN/GTIN, c�digo interno, fabricante, fornecedor, embalagem)",
    ],
    "porque": [
        "Suporta m�ltiplos c�digos por produto com valida����o GTIN e busca exata antes da textual (MDM-003)",
        "Produto sem GTIN pode usar c�digo interno sem inventar GTIN; duplicidade bloqueada por contexto",
    ],
}


def guard(conn) -> bool:
    row = conn.execute(
        "SELECT 1 FROM information_schema.tables "
        "WHERE table_schema='public' AND table_name='produto_identificador'"
    ).fetchone()
    return bool(row)


def forward(conn) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS produto_identificador (
            id BIGSERIAL PRIMARY KEY,
            produto_id INTEGER NOT NULL,
            tipo VARCHAR(20) NOT NULL,
            valor VARCHAR(40) NOT NULL,
            embalagem VARCHAR(10),
            origem VARCHAR(20) NOT NULL DEFAULT 'manual',
            ativo BOOLEAN NOT NULL DEFAULT TRUE,
            criado_por INTEGER,
            criado_em TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            atualizado_em TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            CONSTRAINT chk_identificador_tipo CHECK (
                tipo IN ('ean','gtin','codigo_interno','fabricante','fornecedor','embalagem')
            )
        )
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_produto_identificador_produto "
        "ON produto_identificador (produto_id)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_produto_identificador_valor "
        "ON produto_identificador (valor)"
    )
    conn.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_produto_identificador_ativo "
        "ON produto_identificador (produto_id, tipo, valor) WHERE ativo"
    )
    conn.commit()


def backward(conn) -> None:
    conn.execute("DROP TABLE IF EXISTS produto_identificador")