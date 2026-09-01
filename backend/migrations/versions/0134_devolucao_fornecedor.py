"""Migração 0134 — devolução ao fornecedor vinculada ao recebimento/NF/lote (REC-006)."""
from __future__ import annotations

VERSION = 134
RISCO = "baixa"  # Expand: tabelas novas
NAME = "devolucao_fornecedor"

MUDANCA = {
    "o_que": [
        "Cria devolucao_fornecedor (recebimento, pedido, fornecedor, documento fiscal, motivo, "
        "estado, status aberta/concluida/cancelada) e devolucao_fornecedor_item (produto, lote, quantidade)",
    ],
    "porque": [
        "Não devolve mais que o recebido; lote/série é rastreado; conta a pagar fica correta (REC-006)",
    ],
}


def guard(conn) -> bool:
    row = conn.execute(
        "SELECT 1 FROM information_schema.tables "
        "WHERE table_schema='public' AND table_name='devolucao_fornecedor'"
    ).fetchone()
    return bool(row)


def forward(conn) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS devolucao_fornecedor (
            id BIGSERIAL PRIMARY KEY,
            recebimento_id BIGINT NOT NULL REFERENCES recebimento(id),
            pedido_id INTEGER NOT NULL,
            fornecedor_id INTEGER NOT NULL,
            documento_fiscal VARCHAR(40),
            motivo VARCHAR(20) NOT NULL,
            estado VARCHAR(20) NOT NULL DEFAULT 'avariado',
            observacao TEXT,
            status VARCHAR(20) NOT NULL DEFAULT 'aberta',
            usuario_id INTEGER,
            criado_em TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            CONSTRAINT chk_dev_forn_motivo CHECK (motivo IN ('avariado','erro_quantidade','nao_conforme','devolucao_comercial','outro')),
            CONSTRAINT chk_dev_forn_estado CHECK (estado IN ('avariado','novo','usado','incompleto')),
            CONSTRAINT chk_dev_forn_status CHECK (status IN ('aberta','concluida','cancelada'))
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS devolucao_fornecedor_item (
            id BIGSERIAL PRIMARY KEY,
            devolucao_id BIGINT NOT NULL REFERENCES devolucao_fornecedor(id),
            produto_id INTEGER NOT NULL,
            lote_id INTEGER,
            quantidade NUMERIC(14,3) NOT NULL,
            criado_em TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_dev_item_dev ON devolucao_fornecedor_item (devolucao_id)")
    conn.commit()


def backward(conn) -> None:
    conn.execute("DROP TABLE IF EXISTS devolucao_fornecedor_item")
    conn.execute("DROP TABLE IF EXISTS devolucao_fornecedor")