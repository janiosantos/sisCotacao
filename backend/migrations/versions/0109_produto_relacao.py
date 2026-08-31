"""Migração 0109 — relações entre produtos: equivalentes, substitutos, acessórios e kits (MDM-005)."""
from __future__ import annotations

VERSION = 109
RISCO = "baixa"  # Expand: tabela nova
NAME = "produto_relacao"

MUDANCA = {
    "o_que": [
        "Cria tabela produto_relacao (equivalente, substituto, acessorio, complementar, componente de kit)",
        "Relações tipadas com fator, prioridade, vigência, aprovação, motivo e versão",
    ],
    "porque": [
        "Busca mostra substitutos e complementares; venda só substitui com confirmação; "
        "kits têm composição versionada (MDM-005)",
    ],
}


def guard(conn) -> bool:
    row = conn.execute(
        "SELECT 1 FROM information_schema.tables "
        "WHERE table_schema='public' AND table_name='produto_relacao'"
    ).fetchone()
    return bool(row)


def forward(conn) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS produto_relacao (
            id BIGSERIAL PRIMARY KEY,
            produto_id INTEGER NOT NULL,
            relacionado_id INTEGER NOT NULL,
            tipo VARCHAR(20) NOT NULL,
            fator NUMERIC(12,4) NOT NULL DEFAULT 1,
            prioridade INTEGER NOT NULL DEFAULT 1,
            vigencia_inicio DATE,
            vigencia_fim DATE,
            aprovado BOOLEAN NOT NULL DEFAULT TRUE,
            motivo TEXT,
            ativo BOOLEAN NOT NULL DEFAULT TRUE,
            versao INTEGER NOT NULL DEFAULT 1,
            criado_por INTEGER,
            criado_em TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            atualizado_em TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            CONSTRAINT chk_produto_relacao_tipo CHECK (
                tipo IN ('equivalente','substituto','acessorio','complementar','componente')
            ),
            CONSTRAINT chk_produto_relacao_dif CHECK (produto_id <> relacionado_id),
            CONSTRAINT chk_produto_relacao_fator CHECK (fator > 0)
        )
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_produto_relacao_produto "
        "ON produto_relacao (produto_id)"
    )
    conn.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_produto_relacao_ativo "
        "ON produto_relacao (produto_id, relacionado_id, tipo) WHERE ativo"
    )
    conn.commit()


def backward(conn) -> None:
    conn.execute("DROP TABLE IF EXISTS produto_relacao")