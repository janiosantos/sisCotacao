"""Migração 0139 — pós-venda: RMA/devolução, troca e crédito de cliente (POS-001/POS-002)."""
from __future__ import annotations

VERSION = 139
RISCO = "baixa"  # Expand: tabelas novas
NAME = "posvenda_rma_troca"

MUDANCA = {
    "o_que": [
        "Cria rma (autorização de retorno vinculada à venda/item/lote; estados "
        "solicitada→autorizada→recebida→analisada→concluída/rejeitada; prazo, motivo, condição)",
        "Cria troca (item substituto + diferença) e credito_cliente (saldo de crédito com origem)",
    ],
    "porque": [
        "Devolução acima do vendido é bloqueada; troca calcula diferença; crédito não duplica (POS-001/002)",
    ],
}


def guard(conn) -> bool:
    row = conn.execute(
        "SELECT 1 FROM information_schema.tables "
        "WHERE table_schema='public' AND table_name='rma'"
    ).fetchone()
    return bool(row)


def forward(conn) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS rma (
            id BIGSERIAL PRIMARY KEY,
            orcamento_id INTEGER NOT NULL,
            cliente_id INTEGER,
            produto_id INTEGER NOT NULL,
            lote_id INTEGER,
            quantidade NUMERIC(14,3) NOT NULL,
            motivo VARCHAR(40) NOT NULL,
            condicao VARCHAR(20) NOT NULL DEFAULT 'avariado',
            status VARCHAR(20) NOT NULL DEFAULT 'solicitada',
            data_solicitacao DATE NOT NULL DEFAULT CURRENT_DATE,
            prazo_validade INTEGER NOT NULL DEFAULT 30,
            analise TEXT,
            observacao TEXT,
            criado_em TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            CONSTRAINT chk_rma_motivo CHECK (motivo IN ('defeito','arrependimento','entrega_errada','avariado_transporte','outro')),
            CONSTRAINT chk_rma_condicao CHECK (condicao IN ('avariado','novo','usado','incompleto')),
            CONSTRAINT chk_rma_status CHECK (status IN ('solicitada','autorizada','recebida','analisada','concluida','rejeitada'))
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS troca (
            id BIGSERIAL PRIMARY KEY,
            rma_id BIGINT NOT NULL REFERENCES rma(id),
            produto_novo_id INTEGER NOT NULL,
            quantidade_nova NUMERIC(14,3) NOT NULL,
            diferenca NUMERIC(14,2) NOT NULL DEFAULT 0,
            status VARCHAR(20) NOT NULL DEFAULT 'aberta',
            criado_em TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            CONSTRAINT chk_troca_status CHECK (status IN ('aberta','concluida','cancelada'))
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS credito_cliente (
            id BIGSERIAL PRIMARY KEY,
            cliente_id INTEGER NOT NULL,
            valor NUMERIC(14,2) NOT NULL,
            saldo NUMERIC(14,2) NOT NULL,
            origem VARCHAR(20) NOT NULL,
            origem_id BIGINT,
            status VARCHAR(20) NOT NULL DEFAULT 'aberto',
            criado_em TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            CONSTRAINT uq_credito_origem UNIQUE (origem, origem_id),
            CONSTRAINT chk_credito_status CHECK (status IN ('aberto','utilizado','estornado'))
        )
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_rma_orcamento ON rma (orcamento_id)")
    conn.commit()


def backward(conn) -> None:
    for t in ("credito_cliente", "troca", "rma"):
        conn.execute(f"DROP TABLE IF EXISTS {t}")