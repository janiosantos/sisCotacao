"""Migração 0132 — entrada fiscal XML (NF-e): estende nfe_entrada e cria itens (REC-004)."""
from __future__ import annotations

VERSION = 132
RISCO = "media"  # Expand: estende tabela legada nfe_entrada (colunas novas + índice único); sem drop
NAME = "nfe_entrada"

MUDANCA = {
    "o_que": [
        "nfe_entrada (tabela legada) + chave_acesso (única), fornecedor_id, protocolo, status, "
        "valor_total, emissao — para importação de XML de entrada",
        "Cria nfe_entrada_item (produto vinculável, código fornecedor, EAN, descrição, NCM/CFOP/CST, "
        "unidade, quantidade, valor unitário, status sem_vinculo/vinculado)",
    ],
    "porque": [
        "XML duplicado é rejeitado; item sem vínculo não entra silenciosamente; "
        "fiscal pode corrigir vínculo antes da confirmação (REC-004)",
    ],
}


def guard(conn) -> bool:
    row = conn.execute(
        "SELECT 1 FROM information_schema.columns "
        "WHERE table_name='nfe_entrada' AND column_name='chave_acesso'"
    ).fetchone()
    return bool(row)


def forward(conn) -> None:
    conn.execute("ALTER TABLE nfe_entrada ADD COLUMN IF NOT EXISTS chave_acesso VARCHAR(44)")
    conn.execute("ALTER TABLE nfe_entrada ADD COLUMN IF NOT EXISTS fornecedor_id INTEGER")
    conn.execute("ALTER TABLE nfe_entrada ADD COLUMN IF NOT EXISTS protocolo VARCHAR(30)")
    conn.execute("ALTER TABLE nfe_entrada ADD COLUMN IF NOT EXISTS status VARCHAR(20) NOT NULL DEFAULT 'importado'")
    conn.execute("ALTER TABLE nfe_entrada ADD COLUMN IF NOT EXISTS valor_total NUMERIC(16,4)")
    conn.execute("ALTER TABLE nfe_entrada ADD COLUMN IF NOT EXISTS emissao DATE")
    conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS uq_nfe_entrada_chave_acesso ON nfe_entrada (chave_acesso)")
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS nfe_entrada_item (
            id BIGSERIAL PRIMARY KEY,
            nfe_id BIGINT NOT NULL REFERENCES nfe_entrada(id),
            produto_id INTEGER,
            codigo_fornecedor VARCHAR(40),
            ean VARCHAR(20),
            descricao TEXT,
            ncm VARCHAR(10),
            cfop VARCHAR(10),
            cst VARCHAR(5),
            unidade VARCHAR(10),
            quantidade NUMERIC(14,3),
            valor_unitario NUMERIC(14,4),
            status VARCHAR(20) NOT NULL DEFAULT 'sem_vinculo',
            CONSTRAINT chk_nfe_item_status CHECK (status IN ('sem_vinculo','vinculado'))
        )
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_nfe_item_nfe ON nfe_entrada_item (nfe_id)")
    conn.commit()


def backward(conn) -> None:
    conn.execute("DROP TABLE IF EXISTS nfe_entrada_item")
    for col in ("chave_acesso", "fornecedor_id", "protocolo", "status", "valor_total", "emissao"):
        conn.execute(f"ALTER TABLE nfe_entrada DROP COLUMN IF EXISTS {col}")