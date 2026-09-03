"""Migração 0153 — classificação financeira, competência e rateio."""
from __future__ import annotations

VERSION = 153
RISCO = "melhoria"
NAME = "classificacao_despesas"

MUDANCA = {
    "o_que": [
        "Adiciona natureza econômica e política de rateio ao plano de contas",
        "Adiciona competência, classificação e snapshot em contas a pagar",
        "Cria competências de precificação, rateios e regras financeiras por fornecedor",
    ],
    "porque": [
        "Separar despesas fixas, variáveis, custos diretos e itens não rateáveis",
        "Permitir auditoria histórica sem depender do estado atual da conta",
        "Alimentar a precificação somente com valores elegíveis e aprovados",
    ],
}


def _columns(conn, table: str) -> set[str]:
    rows = conn.execute(
        "SELECT column_name FROM information_schema.columns "
        "WHERE table_schema='public' AND table_name=?",
        (table,),
    ).fetchall()
    return {str(row["column_name"]) for row in rows}


def guard(conn) -> bool:
    plano = _columns(conn, "plano_de_contas")
    pagar = _columns(conn, "contas_pagar")
    tables = conn.execute(
        "SELECT table_name FROM information_schema.tables "
        "WHERE table_schema='public' AND table_name IN "
        "('precificacao_competencia','conta_pagar_rateio','fornecedor_regra_financeira')"
    ).fetchall()
    return {
        "natureza_custo", "politica_rateio", "permite_rateio",
    }.issubset(plano) and {
        "competencia", "elegivel_precificacao", "status_classificacao",
    }.issubset(pagar) and len(tables) == 3


def forward(conn) -> None:
    conn.execute(
        "ALTER TABLE plano_de_contas ADD COLUMN IF NOT EXISTS "
        "natureza_custo TEXT NOT NULL DEFAULT 'fora_precificacao'"
    )
    conn.execute(
        "ALTER TABLE plano_de_contas ADD COLUMN IF NOT EXISTS "
        "politica_rateio TEXT NOT NULL DEFAULT 'nao_incluir'"
    )
    conn.execute(
        "ALTER TABLE plano_de_contas ADD COLUMN IF NOT EXISTS "
        "exige_centro_custo BOOLEAN NOT NULL DEFAULT FALSE"
    )
    conn.execute(
        "ALTER TABLE plano_de_contas ADD COLUMN IF NOT EXISTS "
        "exige_competencia BOOLEAN NOT NULL DEFAULT FALSE"
    )
    conn.execute(
        "ALTER TABLE plano_de_contas ADD COLUMN IF NOT EXISTS "
        "permite_rateio BOOLEAN NOT NULL DEFAULT FALSE"
    )
    conn.execute(
        "ALTER TABLE plano_de_contas ADD COLUMN IF NOT EXISTS "
        "componente_variavel TEXT"
    )
    conn.execute(
        "ALTER TABLE plano_de_contas ADD COLUMN IF NOT EXISTS "
        "atualizado_por BIGINT"
    )
    conn.execute(
        "ALTER TABLE contas_pagar ADD COLUMN IF NOT EXISTS competencia TEXT"
    )
    conn.execute(
        "ALTER TABLE contas_pagar ADD COLUMN IF NOT EXISTS "
        "data_competencia_inicio DATE"
    )
    conn.execute(
        "ALTER TABLE contas_pagar ADD COLUMN IF NOT EXISTS "
        "data_competencia_fim DATE"
    )
    conn.execute(
        "ALTER TABLE contas_pagar ADD COLUMN IF NOT EXISTS "
        "natureza_custo_snapshot TEXT"
    )
    conn.execute(
        "ALTER TABLE contas_pagar ADD COLUMN IF NOT EXISTS "
        "politica_rateio_snapshot TEXT"
    )
    conn.execute(
        "ALTER TABLE contas_pagar ADD COLUMN IF NOT EXISTS "
        "elegivel_precificacao BOOLEAN NOT NULL DEFAULT FALSE"
    )
    conn.execute(
        "ALTER TABLE contas_pagar ADD COLUMN IF NOT EXISTS "
        "componente_precificacao TEXT"
    )
    conn.execute(
        "ALTER TABLE contas_pagar ADD COLUMN IF NOT EXISTS "
        "centro_custo_id BIGINT"
    )
    conn.execute(
        "ALTER TABLE contas_pagar ADD COLUMN IF NOT EXISTS "
        "origem_classificacao TEXT NOT NULL DEFAULT 'pendente'"
    )
    conn.execute(
        "ALTER TABLE contas_pagar ADD COLUMN IF NOT EXISTS "
        "status_classificacao TEXT NOT NULL DEFAULT 'pendente'"
    )
    conn.execute(
        "ALTER TABLE contas_pagar ADD COLUMN IF NOT EXISTS classificado_por BIGINT"
    )
    conn.execute(
        "ALTER TABLE contas_pagar ADD COLUMN IF NOT EXISTS classificado_em TIMESTAMPTZ"
    )
    conn.execute(
        "ALTER TABLE contas_pagar ADD COLUMN IF NOT EXISTS aprovado_por BIGINT"
    )
    conn.execute(
        "ALTER TABLE contas_pagar ADD COLUMN IF NOT EXISTS aprovado_em TIMESTAMPTZ"
    )
    conn.execute(
        "ALTER TABLE contas_pagar ADD COLUMN IF NOT EXISTS observacao_classificacao TEXT"
    )
    conn.execute(
        "ALTER TABLE plano_de_contas DROP CONSTRAINT IF EXISTS plano_contas_natureza_ck"
    )
    conn.execute(
        "ALTER TABLE plano_de_contas ADD CONSTRAINT plano_contas_natureza_ck "
        "CHECK (natureza_custo IN ('fixa','variavel','custo_direto','cmv','nao_rateavel','fora_precificacao'))"
    )
    conn.execute(
        "ALTER TABLE plano_de_contas DROP CONSTRAINT IF EXISTS plano_contas_rateio_ck"
    )
    conn.execute(
        "ALTER TABLE plano_de_contas ADD CONSTRAINT plano_contas_rateio_ck "
        "CHECK (politica_rateio IN ('nao_incluir','ratear_faturamento','ratear_unidades',"
        "'ratear_custo_mercadoria','apropriar_direto','revisao_manual'))"
    )
    conn.execute(
        "ALTER TABLE contas_pagar DROP CONSTRAINT IF EXISTS contas_pagar_classificacao_ck"
    )
    conn.execute(
        "ALTER TABLE contas_pagar ADD CONSTRAINT contas_pagar_classificacao_ck "
        "CHECK (status_classificacao IN ('pendente','classificada','aprovada','rejeitada'))"
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS precificacao_competencia (
            id BIGSERIAL PRIMARY KEY,
            competencia TEXT NOT NULL UNIQUE CHECK (competencia ~ '^[0-9]{4}-[0-9]{2}$'),
            faturamento_base NUMERIC(14,2) NOT NULL DEFAULT 0 CHECK (faturamento_base >= 0),
            faturamento_fonte TEXT NOT NULL DEFAULT 'realizado'
                CHECK (faturamento_fonte IN ('realizado','planejado','media_movel','manual')),
            criterio_apuracao TEXT NOT NULL DEFAULT 'competencia'
                CHECK (criterio_apuracao IN ('competencia','caixa','gerencial','planejado')),
            status TEXT NOT NULL DEFAULT 'aberta'
                CHECK (status IN ('aberta','em_revisao','aprovada','fechada','reaberta')),
            observacao TEXT NOT NULL DEFAULT '',
            criado_por BIGINT,
            aprovado_por BIGINT,
            fechado_por BIGINT,
            criado_em TIMESTAMPTZ NOT NULL DEFAULT now(),
            atualizado_em TIMESTAMPTZ NOT NULL DEFAULT now(),
            aprovado_em TIMESTAMPTZ,
            fechado_em TIMESTAMPTZ
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS conta_pagar_rateio (
            id BIGSERIAL PRIMARY KEY,
            conta_pagar_id BIGINT NOT NULL REFERENCES contas_pagar(id) ON DELETE CASCADE,
            competencia TEXT NOT NULL CHECK (competencia ~ '^[0-9]{4}-[0-9]{2}$'),
            centro_custo_id BIGINT REFERENCES centros_custo(id),
            produto_id BIGINT REFERENCES produtos_cadastro(id),
            percentual NUMERIC(7,4) NOT NULL CHECK (percentual > 0 AND percentual <= 100),
            valor NUMERIC(14,2) NOT NULL CHECK (valor >= 0),
            politica_rateio TEXT NOT NULL,
            elegivel_precificacao BOOLEAN NOT NULL DEFAULT FALSE,
            criado_por BIGINT,
            criado_em TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS fornecedor_regra_financeira (
            id BIGSERIAL PRIMARY KEY,
            fornecedor_id BIGINT NOT NULL REFERENCES fornecedores(id),
            plano_conta_id BIGINT REFERENCES plano_de_contas(id),
            centro_custo_id BIGINT REFERENCES centros_custo(id),
            competencia_padrao TEXT,
            prioridade INTEGER NOT NULL DEFAULT 100,
            ativo BOOLEAN NOT NULL DEFAULT TRUE,
            vigencia_inicio DATE,
            vigencia_fim DATE,
            criado_por BIGINT,
            atualizado_por BIGINT,
            criado_em TIMESTAMPTZ NOT NULL DEFAULT now(),
            atualizado_em TIMESTAMPTZ NOT NULL DEFAULT now(),
            UNIQUE(fornecedor_id)
        )
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_pagar_classificacao ON contas_pagar(status_classificacao, competencia)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_pagar_elegivel ON contas_pagar(competencia, elegivel_precificacao)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_rateio_competencia ON conta_pagar_rateio(competencia, elegivel_precificacao)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_fornecedor_regra_financeira ON fornecedor_regra_financeira(fornecedor_id, ativo)")
    conn.commit()


def backward(conn) -> None:
    conn.execute("DROP TABLE IF EXISTS fornecedor_regra_financeira")
    conn.execute("DROP TABLE IF EXISTS conta_pagar_rateio")
    conn.execute("DROP TABLE IF EXISTS precificacao_competencia")
    conn.execute("ALTER TABLE contas_pagar DROP CONSTRAINT IF EXISTS contas_pagar_classificacao_ck")
    for column in (
        "observacao_classificacao", "aprovado_em", "aprovado_por", "classificado_em",
        "classificado_por", "status_classificacao", "origem_classificacao",
        "centro_custo_id", "componente_precificacao", "elegivel_precificacao",
        "politica_rateio_snapshot", "natureza_custo_snapshot", "data_competencia_fim",
        "data_competencia_inicio", "competencia",
    ):
        conn.execute(f"ALTER TABLE contas_pagar DROP COLUMN IF EXISTS {column}")
    conn.execute("ALTER TABLE plano_de_contas DROP CONSTRAINT IF EXISTS plano_contas_natureza_ck")
    conn.execute("ALTER TABLE plano_de_contas DROP CONSTRAINT IF EXISTS plano_contas_rateio_ck")
    for column in (
        "atualizado_por", "componente_variavel", "permite_rateio",
        "exige_competencia", "exige_centro_custo", "politica_rateio", "natureza_custo",
    ):
        conn.execute(f"ALTER TABLE plano_de_contas DROP COLUMN IF EXISTS {column}")
    conn.commit()
