"""Migração 0150 — dados de relacionamento para relatórios de clientes."""
from __future__ import annotations

VERSION = 150
RISCO = "melhoria"
NAME = "clientes_relatorios"

MUDANCA = {
    "o_que": [
        "Adiciona data de nascimento e preferências de contato ao cadastro de clientes",
        "Cria índices para filtros de relacionamento e aniversário",
    ],
    "porque": [
        "Permitir relatórios de aniversariantes, segmentação e ações comerciais auditáveis",
        "Evitar varredura completa do cadastro em consultas recorrentes",
    ],
}


def guard(conn) -> bool:
    row = conn.execute(
        "SELECT COUNT(*) AS total FROM information_schema.columns "
        "WHERE table_schema='public' AND table_name='clientes' "
        "AND column_name IN ('data_nascimento','consentimento_contato','canal_preferencial','origem_cadastro')"
    ).fetchone()
    return bool(row and int(row["total"] or 0) == 4)


def forward(conn) -> None:
    conn.execute(
        "ALTER TABLE clientes ADD COLUMN IF NOT EXISTS data_nascimento DATE"
    )
    conn.execute(
        "ALTER TABLE clientes ADD COLUMN IF NOT EXISTS consentimento_contato BOOLEAN NOT NULL DEFAULT FALSE"
    )
    conn.execute(
        "ALTER TABLE clientes ADD COLUMN IF NOT EXISTS canal_preferencial TEXT NOT NULL DEFAULT ''"
    )
    conn.execute(
        "ALTER TABLE clientes ADD COLUMN IF NOT EXISTS origem_cadastro TEXT NOT NULL DEFAULT 'manual'"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_clientes_relatorio_perfil "
        "ON clientes (tipo_pessoa, segmento, categoria, ativo)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_clientes_aniversario "
        "ON clientes (data_nascimento) WHERE data_nascimento IS NOT NULL"
    )
    conn.commit()


def backward(conn) -> None:
    conn.execute("DROP INDEX IF EXISTS idx_clientes_aniversario")
    conn.execute("DROP INDEX IF EXISTS idx_clientes_relatorio_perfil")
    conn.execute("ALTER TABLE clientes DROP COLUMN IF EXISTS origem_cadastro")
    conn.execute("ALTER TABLE clientes DROP COLUMN IF EXISTS canal_preferencial")
    conn.execute("ALTER TABLE clientes DROP COLUMN IF EXISTS consentimento_contato")
    conn.execute("ALTER TABLE clientes DROP COLUMN IF EXISTS data_nascimento")
    conn.commit()
