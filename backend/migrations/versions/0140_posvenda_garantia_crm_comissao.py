"""Migração 0140 — pós-venda: garantia com fornecedor/laudo (POS-003), CRM/oportunidade (POS-004) e comissões (POS-005)."""
from __future__ import annotations

VERSION = 140
RISCO = "baixa"  # Expand: colunas/tabelas novas
NAME = "posvenda_garantia_crm_comissao"

MUDANCA = {
    "o_que": [
        "garantia + fornecedor_id, n_serie, laudo, custo, responsabilidade, sla_data",
        "oportunidade (CRM): cliente, vendedor, valor, etapa, próxima ação, motivo de perda",
        "comissao: venda, vendedor, base, percentual, valor, política versionada, reversão",
    ],
    "porque": [
        "Operador acompanha pendência; retorno ao estoque/quarentena rastreado (POS-003)",
        "Carteira filtrável; orçamento perdido exige motivo (POS-004)",
        "Base/percentual congelados no evento; estorno gera reversão (POS-005)",
    ],
}


def guard(conn) -> bool:
    row = conn.execute(
        "SELECT 1 FROM information_schema.columns "
        "WHERE table_name='garantia' AND column_name='fornecedor_id'"
    ).fetchone()
    return bool(row)


def forward(conn) -> None:
    conn.execute("ALTER TABLE garantia ADD COLUMN IF NOT EXISTS fornecedor_id INTEGER")
    conn.execute("ALTER TABLE garantia ADD COLUMN IF NOT EXISTS n_serie VARCHAR(40)")
    conn.execute("ALTER TABLE garantia ADD COLUMN IF NOT EXISTS laudo TEXT")
    conn.execute("ALTER TABLE garantia ADD COLUMN IF NOT EXISTS custo NUMERIC(14,2)")
    conn.execute("ALTER TABLE garantia ADD COLUMN IF NOT EXISTS responsabilidade VARCHAR(20)")
    conn.execute("ALTER TABLE garantia ADD COLUMN IF NOT EXISTS sla_data DATE")
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS oportunidade (
            id BIGSERIAL PRIMARY KEY,
            cliente_id INTEGER,
            vendedor_id INTEGER,
            titulo VARCHAR(120) NOT NULL,
            valor NUMERIC(14,2) NOT NULL DEFAULT 0,
            etapa VARCHAR(30) NOT NULL DEFAULT 'prospeccao',
            status VARCHAR(20) NOT NULL DEFAULT 'aberta',
            motivo_perda VARCHAR(60),
            proxima_acao VARCHAR(120),
            proximo_contato DATE,
            criado_em TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            CONSTRAINT chk_op_status CHECK (status IN ('aberta','perdida','ganha')),
            CONSTRAINT chk_op_etapa CHECK (etapa IN ('prospeccao','qualificacao','proposta','negociacao','fechada'))
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS comissao_politica (
            id BIGSERIAL PRIMARY KEY,
            vendedor_id INTEGER NOT NULL,
            percentual NUMERIC(8,4) NOT NULL DEFAULT 0,
            versao INTEGER NOT NULL DEFAULT 1,
            ativo BOOLEAN NOT NULL DEFAULT TRUE,
            criado_em TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            CONSTRAINT uq_comissao_politica UNIQUE (vendedor_id, versao)
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS comissao (
            id BIGSERIAL PRIMARY KEY,
            orcamento_id INTEGER NOT NULL,
            vendedor_id INTEGER NOT NULL,
            base NUMERIC(14,2) NOT NULL,
            percentual NUMERIC(8,4) NOT NULL,
            valor NUMERIC(14,2) NOT NULL,
            politica_versao INTEGER NOT NULL DEFAULT 1,
            status VARCHAR(20) NOT NULL DEFAULT 'pendente',
            revertida_de BIGINT,
            criado_em TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            CONSTRAINT chk_comissao_status CHECK (status IN ('pendente','paga','revertida')),
            CONSTRAINT uq_comissao_venda UNIQUE (orcamento_id, vendedor_id)
        )
        """
    )
    conn.commit()


def backward(conn) -> None:
    for col in ("fornecedor_id", "n_serie", "laudo", "custo", "responsabilidade", "sla_data"):
        conn.execute(f"ALTER TABLE garantia DROP COLUMN IF EXISTS {col}")
    conn.execute("DROP TABLE IF EXISTS comissao")
    conn.execute("DROP TABLE IF EXISTS oportunidade")