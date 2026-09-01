"""Migração 0138 — cobrança e renegociação: juros/multa e novas parcelas (VEN-006)."""
from __future__ import annotations

VERSION = 138
RISCO = "baixa"  # Expand: colunas/tabela novas
NAME = "cobranca_renegociacao"

MUDANCA = {
    "o_que": [
        "contas_receber + juros_multa, cobranca_recalculada_em, renegociada_de (vínculo)",
        "config_cobranca: juros_dia_pct e multa_pct configuráveis",
        "contas_receber.status + 'renegociada' (amplia CHECK)",
    ],
    "porque": [
        "Parcela vencida é recalculada com política; bloqueios são explicáveis (VEN-006)",
        "Renegociação gera novas parcelas e preserva origem",
    ],
}


def guard(conn) -> bool:
    row = conn.execute(
        "SELECT 1 FROM information_schema.columns "
        "WHERE table_name='contas_receber' AND column_name='juros_multa'"
    ).fetchone()
    return bool(row)


def forward(conn) -> None:
    conn.execute("ALTER TABLE contas_receber ADD COLUMN IF NOT EXISTS juros_multa NUMERIC(14,2) NOT NULL DEFAULT 0")
    conn.execute("ALTER TABLE contas_receber ADD COLUMN IF NOT EXISTS cobranca_recalculada_em TIMESTAMPTZ")
    conn.execute("ALTER TABLE contas_receber ADD COLUMN IF NOT EXISTS renegociada_de BIGINT")
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS config_cobranca (
            id INTEGER PRIMARY KEY,
            juros_dia_pct NUMERIC(8,4) NOT NULL DEFAULT 0.033,
            multa_pct NUMERIC(8,4) NOT NULL DEFAULT 2.0,
            atualizado_em TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """
    )
    conn.execute("INSERT INTO config_cobranca (id) VALUES (1) ON CONFLICT (id) DO NOTHING")
    conn.execute("ALTER TABLE contas_receber DROP CONSTRAINT IF EXISTS contas_receber_status_check")
    conn.execute(
        "ALTER TABLE contas_receber ADD CONSTRAINT contas_receber_status_check"
        " CHECK (status IN ('aberto','parcial','pago','cancelado','renegociada'))"
    )
    conn.commit()


def backward(conn) -> None:
    for col in ("juros_multa", "cobranca_recalculada_em", "renegociada_de"):
        conn.execute(f"ALTER TABLE contas_receber DROP COLUMN IF EXISTS {col}")
    conn.execute("DROP TABLE IF EXISTS config_cobranca")