"""Migração 0127 — alçada de aprovação de compra (COM-010)."""
from __future__ import annotations

VERSION = 127
RISCO = "baixa"  # Expand: tabelas novas
NAME = "alcada_compra"

MUDANCA = {
    "o_que": [
        "Cria alcada_compra (limite por valor/fornecedor/centro_custo, ativo, regras configuráveis)",
        "Cria alcada_aprovacao (registro de aprovação/rejeição com motivo, versão, validade, antes/depois)",
    ],
    "porque": [
        "Usuário sem alçada não aprova; alteração relevante invalida aprovação; auditoria antes/depois (COM-010)",
    ],
}


def guard(conn) -> bool:
    row = conn.execute(
        "SELECT 1 FROM information_schema.tables "
        "WHERE table_schema='public' AND table_name='alcada_compra'"
    ).fetchone()
    return bool(row)


def forward(conn) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS alcada_compra (
            id BIGSERIAL PRIMARY KEY,
            perfil_id INTEGER,
            limite_valor NUMERIC(14,2) NOT NULL DEFAULT 0,
            fornecedor_id INTEGER,
            centro_custo VARCHAR(40),
            exige_aprovacao BOOLEAN NOT NULL DEFAULT TRUE,
            ativo BOOLEAN NOT NULL DEFAULT TRUE,
            criado_em TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS alcada_aprovacao (
            id BIGSERIAL PRIMARY KEY,
            pedido_id INTEGER NOT NULL,
            status VARCHAR(20) NOT NULL,  -- aprovado | rejeitado | invalidado
            aprovador_id INTEGER NOT NULL,
            motivo TEXT,
            antes JSONB,
            depois JSONB,
            versao INTEGER NOT NULL DEFAULT 1,
            criado_em TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            CONSTRAINT chk_alcada_aprov_status CHECK (status IN ('aprovado','rejeitado','invalidado'))
        )
        """
    )
    conn.commit()


def backward(conn) -> None:
    conn.execute("DROP TABLE IF EXISTS alcada_aprovacao")
    conn.execute("DROP TABLE IF EXISTS alcada_compra")