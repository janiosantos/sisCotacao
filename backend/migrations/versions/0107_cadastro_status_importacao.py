"""Migra��ǜo 0107 �?" workflow de cadastro e importa����o idempotente (MDM-006)."""
from __future__ import annotations

VERSION = 107
RISCO = "baixa"  # Expand: coluna com default + tabela nova
NAME = "cadastro_status_importacao"

MUDANCA = {
    "o_que": [
        "Adiciona produtos_cadastro.status_cadastro (rascunho/em_revisao/publicado/bloqueado)",
        "Cria tabela cadastro_importacao para auditoria/idempot��ncia de importa����es em lote",
    ],
    "porque": [
        "Workflow de cadastro com revis��o antes de publicar (MDM-006)",
        "Importa����o pode ser simulada; reprocessar o mesmo arquivo n��o duplica; cada lote possui auditoria",
    ],
}


def guard(conn) -> bool:
    row = conn.execute(
        "SELECT 1 FROM information_schema.columns "
        "WHERE table_name='produtos_cadastro' AND column_name='status_cadastro'"
    ).fetchone()
    return bool(row)


def forward(conn) -> None:
    conn.execute(
        "ALTER TABLE produtos_cadastro "
        "ADD COLUMN IF NOT EXISTS status_cadastro VARCHAR(20) NOT NULL DEFAULT 'publicado'"
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS cadastro_importacao (
            id BIGSERIAL PRIMARY KEY,
            arquivo_nome TEXT NOT NULL,
            hash_conteudo TEXT UNIQUE NOT NULL,
            total INTEGER NOT NULL DEFAULT 0,
            criados INTEGER NOT NULL DEFAULT 0,
            atualizados INTEGER NOT NULL DEFAULT 0,
            erros INTEGER NOT NULL DEFAULT 0,
            status TEXT NOT NULL DEFAULT 'ok',  -- ok | erro
            resumo TEXT,
            criado_por INTEGER,
            criado_em TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_cadastro_importacao_arquivo "
        "ON cadastro_importacao (arquivo_nome)"
    )
    conn.commit()


def backward(conn) -> None:
    conn.execute("DROP TABLE IF EXISTS cadastro_importacao")
    conn.execute("ALTER TABLE produtos_cadastro DROP COLUMN IF EXISTS status_cadastro")