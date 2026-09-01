"""Migração 0142 — transporte e entrega (INT-005): transportadora, SLA, eventos logísticos (sem misturar com fiscal/financeiro)."""
from __future__ import annotations

VERSION = 142
RISCO = "baixa"  # Expand: tabelas/colunas novas
NAME = "transporte_entrega"

MUDANCA = {
    "o_que": [
        "Cria transportadora (nome, CNPJ, telefone, prazo médio) e expedicao_evento (eventos logísticos)",
        "expedicao + transportadora_id, sla_data, data_envio, data_entrega, rastreio",
    ],
    "porque": [
        "Operador identifica o que separar, entregar e rastrear; entrega parcial é possível (INT-005)",
        "Status logístico fica separado do fiscal/financeiro",
    ],
}


def guard(conn) -> bool:
    row = conn.execute(
        "SELECT 1 FROM information_schema.tables "
        "WHERE table_schema='public' AND table_name='transportadora'"
    ).fetchone()
    return bool(row)


def forward(conn) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS transportadora (
            id BIGSERIAL PRIMARY KEY,
            nome VARCHAR(80) NOT NULL,
            cnpj VARCHAR(20),
            telefone VARCHAR(20),
            prazo_medio_dias INTEGER,
            ativo BOOLEAN NOT NULL DEFAULT TRUE,
            criado_em TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """
    )
    conn.execute("ALTER TABLE expedicao ADD COLUMN IF NOT EXISTS transportadora_id INTEGER")
    conn.execute("ALTER TABLE expedicao ADD COLUMN IF NOT EXISTS sla_data DATE")
    conn.execute("ALTER TABLE expedicao ADD COLUMN IF NOT EXISTS data_envio TIMESTAMPTZ")
    conn.execute("ALTER TABLE expedicao ADD COLUMN IF NOT EXISTS data_entrega TIMESTAMPTZ")
    conn.execute("ALTER TABLE expedicao ADD COLUMN IF NOT EXISTS rastreio VARCHAR(40)")
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS expedicao_evento (
            id BIGSERIAL PRIMARY KEY,
            expedicao_id BIGINT NOT NULL REFERENCES expedicao(id),
            evento VARCHAR(30) NOT NULL,
            descricao TEXT,
            responsavel_id INTEGER,
            criado_em TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """
    )
    conn.execute("ALTER TABLE expedicao DROP CONSTRAINT IF EXISTS expedicao_status_check")
    conn.execute(
        "ALTER TABLE expedicao ADD CONSTRAINT expedicao_status_check"
        " CHECK (status IN ('pendente','planejada','separada','enviada','parcialmente_entregue','entregue','cancelada'))"
    )
    conn.commit()


def backward(conn) -> None:
    conn.execute("DROP TABLE IF EXISTS expedicao_evento")
    for col in ("transportadora_id", "sla_data", "data_envio", "data_entrega", "rastreio"):
        conn.execute(f"ALTER TABLE expedicao DROP COLUMN IF EXISTS {col}")
    conn.execute("DROP TABLE IF EXISTS transportadora")