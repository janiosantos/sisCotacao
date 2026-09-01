"""Migração 0121 — desempenho real do fornecedor: lead time, fill rate, atraso (COM-005)."""
from __future__ import annotations

VERSION = 121
RISCO = "baixa"  # Expand: tabela nova
NAME = "fornecedor_desempenho"

MUDANCA = {
    "o_que": [
        "Cria fornecedor_desempenho (fornecedor, janela, médias de lead time, desvio, "
        "fill rate, preço líquido, indisponibilidade, atraso, nº de amostras)",
        "fornecedores + lead_time_override e lead_time_override_motivo (override manual auditado)",
    ],
    "porque": [
        "Sugestão usa lead time real quando houver amostra mínima; pouca amostra = baixa confiança (COM-005)",
        "Comprador pode comparar fornecedor preferencial e alternativa",
    ],
}


def guard(conn) -> bool:
    row = conn.execute(
        "SELECT 1 FROM information_schema.tables "
        "WHERE table_schema='public' AND table_name='fornecedor_desempenho'"
    ).fetchone()
    return bool(row)


def forward(conn) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS fornecedor_desempenho (
            id BIGSERIAL PRIMARY KEY,
            fornecedor_id INTEGER NOT NULL,
            data_inicio DATE,
            data_fim DATE,
            n_pedidos INTEGER NOT NULL DEFAULT 0,
            lead_time_medio NUMERIC(8,2),
            lead_time_desvio NUMERIC(8,2),
            fill_rate NUMERIC(8,4),
            preco_liquido_medio NUMERIC(14,4),
            indisponibilidade_pct NUMERIC(8,4),
            atraso_medio_dias NUMERIC(8,2),
            confianca VARCHAR(20) NOT NULL DEFAULT 'baixa',
            calculado_em TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            CONSTRAINT chk_fd_confianca CHECK (confianca IN ('alta','media','baixa'))
        )
        """
    )
    conn.execute("ALTER TABLE fornecedores ADD COLUMN IF NOT EXISTS lead_time_override INTEGER")
    conn.execute("ALTER TABLE fornecedores ADD COLUMN IF NOT EXISTS lead_time_override_motivo TEXT")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_fd_fornecedor ON fornecedor_desempenho (fornecedor_id)")
    conn.commit()


def backward(conn) -> None:
    conn.execute("DROP TABLE IF EXISTS fornecedor_desempenho")
    conn.execute("ALTER TABLE fornecedores DROP COLUMN IF EXISTS lead_time_override")
    conn.execute("ALTER TABLE fornecedores DROP COLUMN IF EXISTS lead_time_override_motivo")