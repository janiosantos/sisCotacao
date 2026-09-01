"""Migração 0119 — base de demanda: registro consolidado real/projetada, auditável até o documento (COM-003)."""
from __future__ import annotations

VERSION = 119
RISCO = "baixa"  # Expand: tabela nova
NAME = "base_demanda"

MUDANCA = {
    "o_que": [
        "Cria demanda_registro (produto, depósito, data, quantidade, tipo real|projetada, "
        "origem venda|pedido_aberto|reserva|devolucao|obra|projeto|manual, status atendida|perdida|aberta)",
        "Consolidação idempotente: vendas finalizadas, pedidos abertos, reservas, devoluções e consumo manual",
    ],
    "porque": [
        "Demanda auditável até os documentos; pedido cancelado não permanece como demanda (COM-003)",
        "Separa demanda atendida de demanda perdida por ruptura",
    ],
}


def guard(conn) -> bool:
    row = conn.execute(
        "SELECT 1 FROM information_schema.tables "
        "WHERE table_schema='public' AND table_name='demanda_registro'"
    ).fetchone()
    return bool(row)


def forward(conn) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS demanda_registro (
            id BIGSERIAL PRIMARY KEY,
            produto_id INTEGER NOT NULL,
            deposito_id INTEGER,
            data DATE NOT NULL,
            quantidade NUMERIC(14,3) NOT NULL,
            tipo VARCHAR(20) NOT NULL DEFAULT 'real',
            origem VARCHAR(30) NOT NULL,
            origem_id BIGINT,
            status VARCHAR(20) NOT NULL DEFAULT 'atendida',
            motivo_ruptura VARCHAR(60),
            usuario_id INTEGER,
            observacao TEXT,
            criado_em TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            CONSTRAINT uq_demanda_fonte UNIQUE (origem, origem_id, produto_id),
            CONSTRAINT chk_demanda_tipo CHECK (tipo IN ('real','projetada')),
            CONSTRAINT chk_demanda_origem CHECK (origem IN ('venda','pedido_aberto','reserva','devolucao','obra','projeto','manual')),
            CONSTRAINT chk_demanda_status CHECK (status IN ('atendida','perdida','aberta'))
        )
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_demanda_produto_data ON demanda_registro (produto_id, data)")
    conn.commit()


def backward(conn) -> None:
    conn.execute("DROP TABLE IF EXISTS demanda_registro")