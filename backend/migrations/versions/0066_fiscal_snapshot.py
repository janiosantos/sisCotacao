"""Migração 0066 — Snapshot fiscal pós-autorização (skill fiscal-mg §14/17).

Preserva o resultado fiscal efetivamente aplicado a cada documento: histórico
não depende da regra vigente para permanecer interpretável (ADR 0001).
"""
from __future__ import annotations

VERSION = 66
RISCO = "rotina"
NAME = "fiscal_snapshot"

MUDANCA = {
    "o_que": ["Cria fiscal_snapshot com bases/rates/values em JSONB e rastreio de regra/versão/fundamento"],
    "porque": [
        "Snapshot pós-autorização: documento histórico não pode ser recalculado pela regra atual",
        "Responde 'por que esta operação recebeu esta tributação?' (auditoria §22)"
    ],
}


def guard(conn) -> bool:
    return conn.execute(
        "SELECT 1 FROM information_schema.tables WHERE table_name='fiscal_snapshot'"
    ).fetchone() is not None


def forward(conn) -> None:
    autocommit = conn.autocommit
    conn.autocommit = True
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS fiscal_snapshot (
                id BIGSERIAL PRIMARY KEY,
                documento_tipo TEXT NOT NULL DEFAULT 'nfe',
                documento_id BIGINT,
                document_number TEXT DEFAULT '',
                variante_id BIGINT,
                produto_nome TEXT DEFAULT '',
                rule_id BIGINT,
                rule_version INTEGER,
                operation_date TEXT NOT NULL DEFAULT '',
                calculation_date TIMESTAMP NOT NULL DEFAULT now(),
                cfop TEXT DEFAULT '',
                cst TEXT DEFAULT '',
                csosn TEXT DEFAULT '',
                bases JSONB,
                rates JSONB,
                values JSONB,
                legal_reference TEXT DEFAULT '',
                source_url TEXT,
                calculation_inputs JSONB,
                status TEXT NOT NULL DEFAULT 'CALCULATED'
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_fsnapshot_doc"
            " ON fiscal_snapshot (documento_tipo, documento_id)"
        )
    finally:
        conn.autocommit = autocommit


def backward(conn) -> None:
    autocommit = conn.autocommit
    conn.autocommit = True
    try:
        conn.execute("DROP TABLE IF EXISTS fiscal_snapshot")
    finally:
        conn.autocommit = autocommit
