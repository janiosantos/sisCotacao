"""Migração 0113 — parâmetros de planejamento por produto/depósito (EST-005)."""
from __future__ import annotations

VERSION = 113
RISCO = "baixa"  # Expand: tabela nova; estoque_minimo/maximo legados permanecem
NAME = "estoque_parametros"

MUDANCA = {
    "o_que": [
        "Cria tabela estoque_parametro por produto/depósito (política, mínimo, máximo, "
        "ponto de pedido, estoque de segurança, lead time, lote, calendário, fonte do valor)",
        "Substitui a visão simplificada de mínimo/máximo mantendo compatibilidade",
    ],
    "porque": [
        "Parâmetros podem ser manuais ou calculados; alteração registra autor e motivo (EST-005)",
        "O cálculo de reposição (COM-004) usará estes parâmetros sem misturar unidades/depósitos",
    ],
}


def guard(conn) -> bool:
    row = conn.execute(
        "SELECT 1 FROM information_schema.tables "
        "WHERE table_schema='public' AND table_name='estoque_parametro'"
    ).fetchone()
    return bool(row)


def forward(conn) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS estoque_parametro (
            id BIGSERIAL PRIMARY KEY,
            produto_id INTEGER NOT NULL,
            deposito_id INTEGER NOT NULL,
            politica VARCHAR(20) NOT NULL DEFAULT 'manual',  -- manual | calculada
            minimo NUMERIC(14,3),
            maximo NUMERIC(14,3),
            ponto_pedido NUMERIC(14,3),
            estoque_seguranca NUMERIC(14,3),
            lead_time_dias INTEGER,
            lote_minimo NUMERIC(14,3),
            lote_maximo NUMERIC(14,3),
            lote_multiplo NUMERIC(14,3),
            calendario VARCHAR(20),
            fonte_valor VARCHAR(20) NOT NULL DEFAULT 'manual',  -- manual | abc | lead_time_real | custom
            motivo TEXT,
            ativo BOOLEAN NOT NULL DEFAULT TRUE,
            versao INTEGER NOT NULL DEFAULT 1,
            criado_por INTEGER,
            criado_em TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            atualizado_em TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            CONSTRAINT chk_estoque_parametro_politica CHECK (politica IN ('manual','calculada')),
            CONSTRAINT chk_estoque_parametro_fonte CHECK (fonte_valor IN ('manual','abc','lead_time_real','custom'))
        )
        """
    )
    conn.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_estoque_parametro_ativo "
        "ON estoque_parametro (produto_id, deposito_id) WHERE ativo"
    )
    conn.commit()


def backward(conn) -> None:
    conn.execute("DROP TABLE IF EXISTS estoque_parametro")