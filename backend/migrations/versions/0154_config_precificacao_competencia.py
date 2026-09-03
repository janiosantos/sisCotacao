"""Migração 0154 — seleção da competência usada na precificação."""
from __future__ import annotations

VERSION = 154
RISCO = "melhoria"
NAME = "config_precificacao_competencia"

MUDANCA = {
    "o_que": [
        "Adiciona competência aprovada e modo de rateio variável à configuração de preços",
    ],
    "porque": [
        "Tornar explícita a origem das despesas usadas pelo motor de precificação",
        "Evitar que despesas variáveis mensais sejam incluídas sem decisão do financeiro",
    ],
}


def guard(conn) -> bool:
    rows = conn.execute(
        "SELECT COUNT(*) AS n FROM information_schema.columns "
        "WHERE table_schema='public' AND table_name='precificacao_configuracao' "
        "AND column_name IN ('competencia_precificacao','usar_competencia_aprovada',"
        "'incluir_despesas_variaveis_rateadas')"
    ).fetchone()
    return bool(rows and int(rows["n"] or 0) == 3)


def forward(conn) -> None:
    conn.execute(
        "ALTER TABLE precificacao_configuracao ADD COLUMN IF NOT EXISTS competencia_precificacao TEXT"
    )
    conn.execute(
        "ALTER TABLE precificacao_configuracao ADD COLUMN IF NOT EXISTS "
        "usar_competencia_aprovada BOOLEAN NOT NULL DEFAULT TRUE"
    )
    conn.execute(
        "ALTER TABLE precificacao_configuracao ADD COLUMN IF NOT EXISTS "
        "incluir_despesas_variaveis_rateadas BOOLEAN NOT NULL DEFAULT FALSE"
    )
    conn.execute(
        "ALTER TABLE precificacao_configuracao DROP CONSTRAINT IF EXISTS "
        "precificacao_config_competencia_ck"
    )
    conn.execute(
        "ALTER TABLE precificacao_configuracao ADD CONSTRAINT precificacao_config_competencia_ck "
        "CHECK (competencia_precificacao IS NULL OR competencia_precificacao ~ '^[0-9]{4}-(0[1-9]|1[0-2])$')"
    )
    conn.commit()


def backward(conn) -> None:
    conn.execute("ALTER TABLE precificacao_configuracao DROP CONSTRAINT IF EXISTS precificacao_config_competencia_ck")
    conn.execute("ALTER TABLE precificacao_configuracao DROP COLUMN IF EXISTS incluir_despesas_variaveis_rateadas")
    conn.execute("ALTER TABLE precificacao_configuracao DROP COLUMN IF EXISTS usar_competencia_aprovada")
    conn.execute("ALTER TABLE precificacao_configuracao DROP COLUMN IF EXISTS competencia_precificacao")
    conn.commit()
