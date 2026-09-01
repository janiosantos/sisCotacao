"""Migração 0117 — ABC histórica: cálculo versionado por período/critério (COM-001)."""
from __future__ import annotations

VERSION = 117
RISCO = "baixa"  # Expand: tabelas novas; classe_abc legada (bootstrap) permanece como fallback
NAME = "abc_historica"

MUDANCA = {
    "o_que": [
        "Cria abc_calculo (versão do cálculo: critério consumo/receita/margem/quantidade/frequência, "
        "período, depósito, parâmetros/cortes, origem historico|bootstrap, total, acumulado)",
        "Cria abc_calculo_item (produto, valor, acumulado, pct_acumulado, classe, ordem)",
        "produtos_cadastro + abc_origem (historico|bootstrap) para identificar a origem da classe",
    ],
    "porque": [
        "Classe ABC reproduzível com fórmula/período; custo da margem é histórico (COM-001)",
        "ABC estimada (bootstrap) fica identificada como tal; item sem venda aparece separado",
    ],
}


def guard(conn) -> bool:
    row = conn.execute(
        "SELECT 1 FROM information_schema.tables "
        "WHERE table_schema='public' AND table_name='abc_calculo'"
    ).fetchone()
    return bool(row)


def forward(conn) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS abc_calculo (
            id BIGSERIAL PRIMARY KEY,
            criterio VARCHAR(20) NOT NULL,
            data_inicio DATE,
            data_fim DATE,
            deposito_id INTEGER,
            parametros JSONB,
            origem VARCHAR(20) NOT NULL DEFAULT 'historico',
            status VARCHAR(20) NOT NULL DEFAULT 'concluido',
            total NUMERIC(16,4),
            acumulado JSONB,
            criado_por INTEGER,
            criado_em TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            CONSTRAINT chk_abc_criterio CHECK (criterio IN ('consumo','receita','margem','quantidade','frequencia')),
            CONSTRAINT chk_abc_origem CHECK (origem IN ('historico','bootstrap'))
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS abc_calculo_item (
            id BIGSERIAL PRIMARY KEY,
            calculo_id BIGINT NOT NULL REFERENCES abc_calculo(id),
            produto_id INTEGER NOT NULL,
            valor NUMERIC(16,4) NOT NULL,
            acumulado NUMERIC(16,4),
            pct_acumulado NUMERIC(8,4),
            classe VARCHAR(1) NOT NULL,
            ordem INTEGER NOT NULL,
            CONSTRAINT uq_abc_calculo_item UNIQUE (calculo_id, produto_id)
        )
        """
    )
    conn.execute("ALTER TABLE produtos_cadastro ADD COLUMN IF NOT EXISTS abc_origem VARCHAR(20) NOT NULL DEFAULT 'bootstrap'")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_abc_item_calculo ON abc_calculo_item (calculo_id)")
    conn.commit()


def backward(conn) -> None:
    conn.execute("DROP TABLE IF EXISTS abc_calculo_item")
    conn.execute("DROP TABLE IF EXISTS abc_calculo")
    conn.execute("ALTER TABLE produtos_cadastro DROP COLUMN IF EXISTS abc_origem")