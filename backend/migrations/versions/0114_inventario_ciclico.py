"""Migração 0114 — inventário cíclico: ciclo de contagem + contagens com aprovação (EST-006)."""
from __future__ import annotations

VERSION = 114
RISCO = "baixa"  # Expand: tabelas novas; ajuste continua via fato 'inventario' no ledger
NAME = "inventario_ciclico"

MUDANCA = {
    "o_que": [
        "Cria inventario_ciclo (ciclo de contagem por depósito) e inventario_contagem "
        "(lista de contagem com saldo esperado, contado, executor e status)",
        "Ajuste de saldo só ocorre após aprovação do ciclo (fato 'inventario' no ledger)",
    ],
    "porque": [
        "Diferença de inventário é explicável via ledger; ciclo registra executor e data (EST-006)",
        "Aprovação antes de ajustar evita divergência não autorizada",
    ],
}


def guard(conn) -> bool:
    row = conn.execute(
        "SELECT 1 FROM information_schema.tables "
        "WHERE table_schema='public' AND table_name='inventario_ciclo'"
    ).fetchone()
    return bool(row)


def forward(conn) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS inventario_ciclo (
            id BIGSERIAL PRIMARY KEY,
            deposito_id INTEGER NOT NULL,
            nome VARCHAR(100) NOT NULL,
            status VARCHAR(20) NOT NULL DEFAULT 'planejado',
            criado_por INTEGER,
            criado_em TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            fechado_em TIMESTAMPTZ,
            CONSTRAINT chk_inv_ciclo_status CHECK (
                status IN ('planejado','em_andamento','aprovado','ajustado','cancelado'))
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS inventario_contagem (
            id BIGSERIAL PRIMARY KEY,
            ciclo_id BIGINT NOT NULL REFERENCES inventario_ciclo(id),
            produto_id INTEGER NOT NULL,
            saldo_esperado NUMERIC(14,3) NOT NULL DEFAULT 0,
            quantidade_contada NUMERIC(14,3),
            executor_id INTEGER,
            contada_em TIMESTAMPTZ,
            status VARCHAR(20) NOT NULL DEFAULT 'pendente',
            aprovado_por INTEGER,
            aprovado_em TIMESTAMPTZ,
            observacao TEXT,
            CONSTRAINT uq_inv_contagem UNIQUE (ciclo_id, produto_id),
            CONSTRAINT chk_inv_contagem_status CHECK (
                status IN ('pendente','conferido','divergente','ok','ajustado'))
        )
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_inv_contagem_ciclo ON inventario_contagem (ciclo_id)"
    )
    conn.commit()


def backward(conn) -> None:
    conn.execute("DROP TABLE IF EXISTS inventario_contagem")
    conn.execute("DROP TABLE IF EXISTS inventario_ciclo")