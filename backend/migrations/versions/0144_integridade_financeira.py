"""Migração 0144 — idempotência financeira e origem de recebimentos.

Expande os ledgers existentes sem remover contrato: lançamentos de caixa podem
ser protegidos contra retry e títulos gerados pelo recebimento passam a ter uma
chave única por recebimento/parcela.
"""
from __future__ import annotations

VERSION = 144
RISCO = "rotina"
NAME = "integridade_financeira"

MUDANCA = {
    "o_que": [
        "Adiciona idempotency_key ao caixa e índice único para lançamentos",
        "Impede duplicidade de título a pagar por recebimento e parcela",
        "Registra o tipo do título associado à conciliação bancária",
    ],
    "porque": [
        "Retry de confirmação não pode duplicar entrada ou saída de caixa",
        "Recebimentos parciais precisam manter origem financeira rastreável",
    ],
}


def guard(conn) -> bool:
    coluna = conn.execute(
        "SELECT 1 FROM information_schema.columns "
        "WHERE table_schema='public' AND table_name='caixa_movimento' "
        "AND column_name='idempotency_key'"
    ).fetchone()
    tipo_matching = conn.execute(
        "SELECT 1 FROM information_schema.columns "
        "WHERE table_schema='public' AND table_name='extrato_bancario' "
        "AND column_name='matching_conta_tipo'"
    ).fetchone()
    indice = conn.execute(
        "SELECT 1 FROM pg_indexes WHERE schemaname='public' "
        "AND indexname='uq_contas_pagar_recebimento_parcela'"
    ).fetchone()
    return bool(coluna and tipo_matching and indice)


def forward(conn) -> None:
    conn.execute(
        "ALTER TABLE caixa_movimento ADD COLUMN IF NOT EXISTS idempotency_key VARCHAR(100)"
    )
    conn.execute(
        "ALTER TABLE extrato_bancario ADD COLUMN IF NOT EXISTS matching_conta_tipo VARCHAR(20)"
    )
    conn.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_caixa_mov_idempotencia "
        "ON caixa_movimento (idempotency_key) WHERE idempotency_key IS NOT NULL"
    )
    conn.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_contas_pagar_recebimento_parcela "
        "ON contas_pagar (origem_tipo, origem_id, parcela) "
        "WHERE origem_tipo='recebimento_compra' AND origem_id IS NOT NULL"
    )
    conn.commit()


def backward(conn) -> None:
    conn.execute("DROP INDEX IF EXISTS uq_contas_pagar_recebimento_parcela")
    conn.execute("DROP INDEX IF EXISTS uq_caixa_mov_idempotencia")
    conn.execute("ALTER TABLE caixa_movimento DROP COLUMN IF EXISTS idempotency_key")
    conn.execute("ALTER TABLE extrato_bancario DROP COLUMN IF EXISTS matching_conta_tipo")
