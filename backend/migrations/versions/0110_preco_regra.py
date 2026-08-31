"""Migração 0110 — regras de preço com prioridade, contexto e vigência (MDM-007)."""
from __future__ import annotations

VERSION = 110
RISCO = "baixa"  # Expand: tabela nova, motor preserva a ordem tabela→motor→base
NAME = "preco_regra"

MUDANCA = {
    "o_que": [
        "Cria tabela preco_regra (preço por cliente/segmento/canal/quantidade com prioridade e vigência)",
        "O motor devolve a regra aplicada com explicação; margem mínima por regra alimenta a alçada (DECISAO-008)",
    ],
    "porque": [
        "O mesmo item em contextos diferentes deve mostrar a regra aplicada (MDM-007)",
        "Rollback comportamental é possível desativando a regra; não altera tabelas/revisões existentes",
    ],
}


def guard(conn) -> bool:
    row = conn.execute(
        "SELECT 1 FROM information_schema.tables "
        "WHERE table_schema='public' AND table_name='preco_regra'"
    ).fetchone()
    return bool(row)


def forward(conn) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS preco_regra (
            id BIGSERIAL PRIMARY KEY,
            produto_id INTEGER NOT NULL,
            prioridade INTEGER NOT NULL DEFAULT 10,
            canal VARCHAR(20),
            cliente_id INTEGER,
            segmento VARCHAR(30),
            quantidade_min NUMERIC(14,2),
            preco NUMERIC(14,2),
            desconto_pct NUMERIC(6,2),
            margem_minima_pct NUMERIC(6,2),
            vigencia_inicio TIMESTAMPTZ,
            vigencia_fim TIMESTAMPTZ,
            motivo TEXT,
            ativo BOOLEAN NOT NULL DEFAULT TRUE,
            versao INTEGER NOT NULL DEFAULT 1,
            criado_por INTEGER,
            criado_em TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            atualizado_em TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            CONSTRAINT chk_preco_regra_preco CHECK (
                preco IS NULL OR preco >= 0
            ),
            CONSTRAINT chk_preco_regra_desconto CHECK (
                desconto_pct IS NULL OR desconto_pct BETWEEN 0 AND 100
            ),
            CONSTRAINT chk_preco_regra_meio CHECK (
                preco IS NOT NULL OR desconto_pct IS NOT NULL
            )
        )
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_preco_regra_produto "
        "ON preco_regra (produto_id)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_preco_regra_vigencia "
        "ON preco_regra (produto_id, vigencia_inicio, vigencia_fim) WHERE ativo"
    )
    conn.commit()


def backward(conn) -> None:
    conn.execute("DROP TABLE IF EXISTS preco_regra")