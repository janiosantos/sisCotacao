"""Migração 0135 — sessão de caixa e terminal: abertura, suprimento, sangria, fechamento (VEN-004)."""
from __future__ import annotations

VERSION = 135
RISCO = "baixa"  # Expand: tabela nova + coluna em caixa_movimento
NAME = "caixa_sessao"

MUDANCA = {
    "o_que": [
        "Cria caixa_sessao (depósito, operador, terminal, saldo inicial, status aberta/fechada, "
        "saldo esperado/contado/diferença, justificativa, aprovação)",
        "caixa_movimento + sessao_id (vínculo dos movimentos à sessão)",
    ],
    "porque": [
        "Dois operadores não usam sessão indevida; fechamento bloqueia novos movimentos; "
        "relatório reconcilia caixa e contas (VEN-004)",
    ],
}


def guard(conn) -> bool:
    row = conn.execute(
        "SELECT 1 FROM information_schema.tables "
        "WHERE table_schema='public' AND table_name='caixa_sessao'"
    ).fetchone()
    return bool(row)


def forward(conn) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS caixa_sessao (
            id BIGSERIAL PRIMARY KEY,
            deposito_id INTEGER NOT NULL DEFAULT 1,
            operador_id INTEGER NOT NULL,
            terminal VARCHAR(20),
            saldo_inicial NUMERIC(14,2) NOT NULL DEFAULT 0,
            status VARCHAR(10) NOT NULL DEFAULT 'aberta',
            abertura_em TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            fechamento_em TIMESTAMPTZ,
            saldo_esperado NUMERIC(14,2),
            saldo_contado NUMERIC(14,2),
            diferenca NUMERIC(14,2),
            justificativa TEXT,
            aprovador_id INTEGER,
            aprovado_em TIMESTAMPTZ,
            CONSTRAINT chk_caixa_sessao_status CHECK (status IN ('aberta','fechada'))
        )
        """
    )
    conn.execute("ALTER TABLE caixa_movimento ADD COLUMN IF NOT EXISTS sessao_id BIGINT")
    conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS uq_caixa_sessao_aberta ON caixa_sessao (operador_id) WHERE status='aberta'")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_caixa_mov_sessao ON caixa_movimento (sessao_id)")
    conn.commit()


def backward(conn) -> None:
    conn.execute("DROP TABLE IF EXISTS caixa_sessao")
    conn.execute("ALTER TABLE caixa_movimento DROP COLUMN IF EXISTS sessao_id")