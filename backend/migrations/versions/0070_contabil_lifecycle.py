"""Migração 0070 — Contabilidade por eventos e lifecycle do documento fiscal.

- lancamento_contabil: pré-lançamentos espelho idempotentes (débito/crédito)
  alimentados por eventos de negócio, contra o plano_contas existente;
- fiscal_documento ganha lifecycle completo (rascunho..contingência) e
  fiscal_document_xml para retenção do XML autorizado (ADR AGENT-produtos).
"""
from __future__ import annotations

VERSION = 70
RISCO = "rotina"
NAME = "contabil_lifecycle"

MUDANCA = {
    "o_que": [
        "Cria lancamento_contabil (debito_id, credito_id FK plano_contas, valor NUMERIC, idempotency_key UNIQUE)",
        "Adiciona lifecycle em documentos_fiscais (rascunho/validando/autorizado/rejeitado/cancelado/inutilizado/contingencia)",
        "Cria fiscal_document_xml para retenção do XML/protocolo",
    ],
    "porque": [
        "Contabilidade e fiscal recebem eventos de negócio com idempotência, período e origem rastreável",
        "XML autorizado preservado sem alterar documentos emitidos"
    ],
}


def guard(conn) -> bool:
    return conn.execute(
        "SELECT 1 FROM information_schema.tables WHERE table_name='lancamento_contabil'"
    ).fetchone() is not None


def forward(conn) -> None:
    ac = conn.autocommit
    conn.autocommit = True
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS lancamento_contabil (
                id BIGSERIAL PRIMARY KEY,
                evento_tipo TEXT NOT NULL,
                evento_id BIGINT NOT NULL,
                idempotency_key TEXT NOT NULL UNIQUE,
                debito_conta_id BIGINT REFERENCES plano_de_contas(id),
                credito_conta_id BIGINT REFERENCES plano_de_contas(id),
                valor NUMERIC(14,2) NOT NULL,
                historico TEXT NOT NULL DEFAULT '',
                periodo_competencia TEXT NOT NULL DEFAULT '',
                origem_tipo TEXT NOT NULL DEFAULT '',
                criado_em TIMESTAMP NOT NULL DEFAULT now()
            )
            """
        )
        conn.execute(
            "ALTER TABLE documentos_fiscais"
            " ADD COLUMN IF NOT EXISTS lifecycle TEXT NOT NULL DEFAULT 'rascunho'"
            " CHECK (lifecycle IN ('rascunho','validando','autorizado','rejeitado',"
            "'cancelado','inutilizado','contingencia'))"
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS fiscal_document_xml (
                id BIGSERIAL PRIMARY KEY,
                documento_fiscal_id BIGINT NOT NULL,
                xml TEXT NOT NULL,
                protocolo TEXT DEFAULT '',
                recebido_em TIMESTAMP NOT NULL DEFAULT now()
            )
            """
        )
    finally:
        conn.autocommit = ac


def backward(conn) -> None:
    ac = conn.autocommit
    conn.autocommit = True
    try:
        conn.execute("DROP TABLE IF EXISTS fiscal_document_xml")
        conn.execute("DROP TABLE IF EXISTS lancamento_contabil")
        conn.execute("ALTER TABLE documentos_fiscais DROP COLUMN IF EXISTS lifecycle")
    finally:
        conn.autocommit = ac
