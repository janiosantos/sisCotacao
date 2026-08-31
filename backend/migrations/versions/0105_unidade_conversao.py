"""Migra��ǜo 0105 �?" convers��es de unidade por produto/embalagem (MDM-002)."""
from __future__ import annotations

VERSION = 105
RISCO = "baixa"  # Expand: tabela nova, sem alterar contrato existente
NAME = "unidade_conversao"

MUDANCA = {
    "o_que": [
        "Cria tabela unidade_conversao (convers��es versionadas por produto/embalagem)",
    ],
    "porque": [
        "Suporta 1 CX = N UN, 1 RL = N M e fracionamento com unidade base e auditoria (MDM-002)",
        "Preserva unidade_venda/fator_conversao atuais durante a migra����o",
    ],
}


def guard(conn) -> bool:
    row = conn.execute(
        "SELECT 1 FROM information_schema.tables "
        "WHERE table_schema='public' AND table_name='unidade_conversao'"
    ).fetchone()
    return bool(row)


def forward(conn) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS unidade_conversao (
            id BIGSERIAL PRIMARY KEY,
            produto_id INTEGER NOT NULL,
            unidade_origem VARCHAR(10) NOT NULL,
            unidade_destino VARCHAR(10) NOT NULL,
            fator NUMERIC(18,6) NOT NULL CHECK (fator > 0),
            unidade_base VARCHAR(10) NOT NULL,
            ativo BOOLEAN NOT NULL DEFAULT TRUE,
            versao INTEGER NOT NULL DEFAULT 1,
            criado_por INTEGER,
            criado_em TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            atualizado_em TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_unidade_conversao_produto "
        "ON unidade_conversao (produto_id)"
    )
    conn.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_unidade_conversao_ativo "
        "ON unidade_conversao (produto_id, unidade_origem) WHERE ativo"
    )
    conn.commit()


def backward(conn) -> None:
    conn.execute("DROP TABLE IF EXISTS unidade_conversao")