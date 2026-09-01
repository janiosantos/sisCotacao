"""Migração 0141 — infraestrutura: idempotência central (ARC-003), auditoria de eventos (ARC-006) e conciliação bancária (INT-001)."""
from __future__ import annotations

VERSION = 141
RISCO = "baixa"  # Expand: tabelas novas
NAME = "infra_idempotencia_auditoria_conciliacao"

MUDANCA = {
    "o_que": [
        "idempotencia: chave única por operação/escopo, payload_hash, resultado (retry devolve o anterior)",
        "auditoria_evento: ator (Bearer), ação, alvo, antes/depois mascarado, motivo, IP, correlation_id",
        "conta_bancaria e movimento_bancario: importação de extrato e conciliação rastreável",
    ],
    "porque": [
        "Retry não repete efeito; chave reutilizada com payload diferente é rejeitada (ARC-003)",
        "Gestor rastreia preço/estoque/alçada/fiscal/financeiro por correlation_id (ARC-006)",
        "Extrato não cria baixa automática sem regra; conciliação manual é rastreável (INT-001)",
    ],
}


def guard(conn) -> bool:
    row = conn.execute(
        "SELECT 1 FROM information_schema.tables "
        "WHERE table_schema='public' AND table_name='idempotencia'"
    ).fetchone()
    return bool(row)


def forward(conn) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS idempotencia (
            chave VARCHAR(100) PRIMARY KEY,
            escopo VARCHAR(40) NOT NULL,
            payload_hash CHAR(40) NOT NULL,
            resultado JSONB,
            criado_em TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS auditoria_evento (
            id BIGSERIAL PRIMARY KEY,
            ator_id INTEGER,
            ator_login VARCHAR(80),
            acao VARCHAR(60) NOT NULL,
            alvo_tipo VARCHAR(40),
            alvo_id VARCHAR(40),
            antes JSONB,
            depois JSONB,
            motivo TEXT,
            ip VARCHAR(45),
            correlation_id VARCHAR(64),
            criado_em TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_aud_evento_alvo ON auditoria_evento (alvo_tipo, alvo_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_aud_evento_corr ON auditoria_evento (correlation_id)")
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS conta_bancaria (
            id BIGSERIAL PRIMARY KEY,
            banco VARCHAR(40) NOT NULL,
            agencia VARCHAR(10),
            conta VARCHAR(20),
            saldo_atual NUMERIC(14,2) NOT NULL DEFAULT 0,
            ativo BOOLEAN NOT NULL DEFAULT TRUE,
            criado_em TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS extrato_bancario (
            id BIGSERIAL PRIMARY KEY,
            conta_id BIGINT NOT NULL REFERENCES conta_bancaria(id),
            data TEXT NOT NULL,
            descricao TEXT,
            valor NUMERIC(14,2) NOT NULL,
            documento VARCHAR(60),
            status VARCHAR(20) NOT NULL DEFAULT 'importado',
            matching_conta_id BIGINT,
            aprovado_por INTEGER,
            aprovado_em TIMESTAMPTZ,
            idempotencia_key VARCHAR(64),
            criado_em TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            CONSTRAINT chk_extrato_status CHECK (status IN ('importado','sugerido','conciliado','rejeitado')),
            CONSTRAINT uq_extrato_idemp UNIQUE (conta_id, idempotencia_key)
        )
        """
    )
    conn.commit()


def backward(conn) -> None:
    for t in ("extrato_bancario", "conta_bancaria", "auditoria_evento", "idempotencia"):
        conn.execute(f"DROP TABLE IF EXISTS {t}")