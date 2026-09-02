"""Migração 0148 — vínculo transacional entre indicação e venda concluída."""
from __future__ import annotations

VERSION = 148
RISCO = "moderada"
NAME = "indicacao_orcamento"

MUDANCA = {
    "o_que": ["Adiciona indicacao_id ao orçamento com FK para a indicação"],
    "porque": ["A bonificação deve nascer do vínculo auditável e da finalização da venda"],
}


def guard(conn) -> bool:
    row = conn.execute(
        "SELECT 1 FROM information_schema.columns WHERE table_schema='public' "
        "AND table_name='orcamentos' AND column_name='indicacao_id'"
    ).fetchone()
    return bool(row)


def forward(conn) -> None:
    conn.execute(
        "ALTER TABLE orcamentos ADD COLUMN IF NOT EXISTS indicacao_id BIGINT "
        "REFERENCES parceiro_indicacao(id)"
    )
    conn.execute("CREATE INDEX IF NOT EXISTS ix_orcamentos_indicacao ON orcamentos (indicacao_id)")
    conn.commit()


def backward(conn) -> None:
    conn.execute("DROP INDEX IF EXISTS ix_orcamentos_indicacao")
    conn.execute("ALTER TABLE orcamentos DROP COLUMN IF EXISTS indicacao_id")
