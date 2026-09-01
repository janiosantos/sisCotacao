"""Migração 0129 — documento de recebimento com conferência parcial (REC-001)."""
from __future__ import annotations

VERSION = 129
RISCO = "baixa"  # Expand: tabelas novas; recebimento simplificado permanece como fallback (flag NOVO_RECEBIMENTO)
NAME = "recebimento_documento"

MUDANCA = {
    "o_que": [
        "Cria recebimento (cabeçalho: pedido, fornecedor, depósito, operador, documento fiscal, "
        "data, status aberto/conferido/finalizado/cancelado) e recebimento_item "
        "(pedido_item, produto, qtd pedido/recebida/aceita/recusada/avariada, status)",
        "Retry não duplica (UNIQUE pedido+documento_fiscal); conferência parcial e recebimentos múltiplos",
    ],
    "porque": [
        "Dois recebimentos do mesmo pedido são permitidos sem ultrapassar saldo; pedido atualiza status (REC-001)",
    ],
}


def guard(conn) -> bool:
    row = conn.execute(
        "SELECT 1 FROM information_schema.tables "
        "WHERE table_schema='public' AND table_name='recebimento'"
    ).fetchone()
    return bool(row)


def forward(conn) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS recebimento (
            id BIGSERIAL PRIMARY KEY,
            pedido_id INTEGER NOT NULL,
            fornecedor_id INTEGER NOT NULL,
            deposito_id INTEGER NOT NULL DEFAULT 1,
            operador_id INTEGER,
            documento_fiscal VARCHAR(40),
            data_recebimento DATE NOT NULL DEFAULT CURRENT_DATE,
            status VARCHAR(20) NOT NULL DEFAULT 'aberto',
            criado_em TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            CONSTRAINT uq_recebimento_doc UNIQUE (pedido_id, documento_fiscal),
            CONSTRAINT chk_recebimento_status CHECK (status IN ('aberto','conferido','finalizado','cancelado'))
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS recebimento_item (
            id BIGSERIAL PRIMARY KEY,
            recebimento_id BIGINT NOT NULL REFERENCES recebimento(id),
            pedido_item_id INTEGER NOT NULL,
            produto_id INTEGER NOT NULL,
            qtd_pedido NUMERIC(14,3) NOT NULL,
            qtd_recebida NUMERIC(14,3) NOT NULL DEFAULT 0,
            qtd_aceita NUMERIC(14,3),
            qtd_recusada NUMERIC(14,3) NOT NULL DEFAULT 0,
            qtd_avariada NUMERIC(14,3) NOT NULL DEFAULT 0,
            status VARCHAR(20) NOT NULL DEFAULT 'pendente',
            CONSTRAINT chk_receb_item_status CHECK (status IN ('pendente','recebido','aceito','recusado','avariado'))
        )
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_receb_pedido ON recebimento (pedido_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_receb_item_rec ON recebimento_item (recebimento_id)")
    conn.commit()


def backward(conn) -> None:
    conn.execute("DROP TABLE IF EXISTS recebimento_item")
    conn.execute("DROP TABLE IF EXISTS recebimento")