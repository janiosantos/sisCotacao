"""Migração 0151 — premissas persistidas da metodologia de precificação."""
from __future__ import annotations

VERSION = 151
RISCO = "melhoria"
NAME = "metodologia_precificacao"

MUDANCA = {
    "o_que": [
        "Cria configuração única de faturamento, despesas e tributos da formação de preço",
        "Adiciona método divisor às tabelas de preço sem remover margem/markup legados",
    ],
    "porque": [
        "Persistir premissas auditáveis em vez de manter parâmetros somente na tela",
        "Reproduzir a metodologia da planilha com compatibilidade retroativa",
    ],
}


def guard(conn) -> bool:
    table = conn.execute(
        "SELECT 1 FROM information_schema.tables "
        "WHERE table_schema='public' AND table_name='precificacao_configuracao'"
    ).fetchone()
    column = conn.execute(
        "SELECT 1 FROM information_schema.columns "
        "WHERE table_schema='public' AND table_name='tabelas_preco' AND column_name='metodologia'"
    ).fetchone()
    return bool(table and column)


def forward(conn) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS precificacao_configuracao (
            id SMALLINT PRIMARY KEY CHECK (id = 1),
            faturamento_mensal NUMERIC(14,2) NOT NULL DEFAULT 0 CHECK (faturamento_mensal >= 0),
            despesa_fixa_mensal NUMERIC(14,2) NOT NULL DEFAULT 0 CHECK (despesa_fixa_mensal >= 0),
            despesa_variavel_mensal NUMERIC(14,2) NOT NULL DEFAULT 0 CHECK (despesa_variavel_mensal >= 0),
            imposto_simples_pct NUMERIC(7,4) NOT NULL DEFAULT 0 CHECK (imposto_simples_pct BETWEEN 0 AND 100),
            imposto_icms_pct NUMERIC(7,4) NOT NULL DEFAULT 0 CHECK (imposto_icms_pct BETWEEN 0 AND 100),
            imposto_pis_pct NUMERIC(7,4) NOT NULL DEFAULT 0 CHECK (imposto_pis_pct BETWEEN 0 AND 100),
            imposto_cofins_pct NUMERIC(7,4) NOT NULL DEFAULT 0 CHECK (imposto_cofins_pct BETWEEN 0 AND 100),
            imposto_ir_pct NUMERIC(7,4) NOT NULL DEFAULT 0 CHECK (imposto_ir_pct BETWEEN 0 AND 100),
            imposto_csll_pct NUMERIC(7,4) NOT NULL DEFAULT 0 CHECK (imposto_csll_pct BETWEEN 0 AND 100),
            ibs_pct NUMERIC(7,4) NOT NULL DEFAULT 0 CHECK (ibs_pct BETWEEN 0 AND 100),
            cbs_pct NUMERIC(7,4) NOT NULL DEFAULT 0 CHECK (cbs_pct BETWEEN 0 AND 100),
            taxa_cartao_pct NUMERIC(7,4) NOT NULL DEFAULT 0 CHECK (taxa_cartao_pct BETWEEN 0 AND 100),
            atividade TEXT NOT NULL DEFAULT 'comercio' CHECK (atividade IN ('comercio','servicos','industria')),
            usar_referencia_atividade BOOLEAN NOT NULL DEFAULT TRUE,
            cenario_tributario TEXT NOT NULL DEFAULT 'atual' CHECK (cenario_tributario IN ('atual','reforma')),
            criado_em TIMESTAMPTZ NOT NULL DEFAULT now(),
            atualizado_em TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    conn.execute(
        "INSERT INTO precificacao_configuracao (id) VALUES (1) ON CONFLICT (id) DO NOTHING"
    )
    conn.execute(
        "ALTER TABLE tabelas_preco ADD COLUMN IF NOT EXISTS metodologia TEXT NOT NULL DEFAULT 'divisor'"
    )
    conn.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint
                WHERE conname = 'tabelas_preco_metodologia_ck'
            ) THEN
                ALTER TABLE tabelas_preco ADD CONSTRAINT tabelas_preco_metodologia_ck
                CHECK (metodologia IN ('divisor','markup_custo'));
            END IF;
        END $$
        """
    )
    conn.commit()


def backward(conn) -> None:
    conn.execute("ALTER TABLE tabelas_preco DROP CONSTRAINT IF EXISTS tabelas_preco_metodologia_ck")
    conn.execute("ALTER TABLE tabelas_preco DROP COLUMN IF EXISTS metodologia")
    conn.execute("DROP TABLE IF EXISTS precificacao_configuracao")
    conn.commit()
