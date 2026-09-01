"""Migração 0137 — pagamentos por pedido: entidade com valor, forma, taxa, provedor, status, idempotência e estorno (VEN-003)."""
from __future__ import annotations

VERSION = 137
RISCO = "baixa"  # Expand: tabela nova
NAME = "orcamento_pagamento"

MUDANCA = {
    "o_que": [
        "Cria orcamento_pagamento (forma, valor, taxa, provedor, bandeira, código de autorização, "
        "status pendente/confirmado/estornado, idempotency_key única por orçamento)",
    ],
    "porque": [
        "Soma dos pagamentos fecha o total; troco só em dinheiro; pagamento pendente não marca "
        "venda como paga; retry não duplica; estorno reverte (VEN-003)",
    ],
}


def guard(conn) -> bool:
    row = conn.execute(
        "SELECT 1 FROM information_schema.tables "
        "WHERE table_schema='public' AND table_name='orcamento_pagamento'"
    ).fetchone()
    return bool(row)


def forward(conn) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS orcamento_pagamento (
            id BIGSERIAL PRIMARY KEY,
            orcamento_id INTEGER NOT NULL,
            forma VARCHAR(20) NOT NULL,
            valor NUMERIC(14,2) NOT NULL,
            taxa NUMERIC(10,4) NOT NULL DEFAULT 0,
            provedor VARCHAR(40),
            bandeira VARCHAR(20),
            codigo_autorizacao VARCHAR(40),
            status VARCHAR(20) NOT NULL DEFAULT 'pendente',
            idempotency_key VARCHAR(64),
            criado_em TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            confirmado_em TIMESTAMPTZ,
            estornado_em TIMESTAMPTZ,
            CONSTRAINT uq_pagamento_idemp UNIQUE (orcamento_id, idempotency_key),
            CONSTRAINT chk_pag_status CHECK (status IN ('pendente','confirmado','estornado'))
        )
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_pag_orcamento ON orcamento_pagamento (orcamento_id)")
    conn.commit()


def backward(conn) -> None:
    conn.execute("DROP TABLE IF EXISTS orcamento_pagamento")