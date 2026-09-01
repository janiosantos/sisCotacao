"""Migração 0131 — conferência de três vias: pedido × recebimento × NF, tolerâncias e aprovação (REC-003)."""
from __future__ import annotations

VERSION = 131
RISCO = "baixa"  # Expand: colunas/tabela novas
NAME = "recebimento_tres_vias"

MUDANCA = {
    "o_que": [
        "recebimento + status_tres_vias (aguardando_conferencia/divergente/aprovado/rejeitado), "
        "divergencia_aprovada_por/em, divergencia_rejeitada_motivo",
        "recebimento_divergencia: por produto/tipo (quantidade|preco|fiscal), pct, dentro da tolerância",
    ],
    "porque": [
        "Diferença de preço/quantidade/fiscal fica visível; tolerância não esconde divergência; "
        "só aprovação gera efeitos definitivos (REC-003)",
    ],
}


def guard(conn) -> bool:
    row = conn.execute(
        "SELECT 1 FROM information_schema.tables "
        "WHERE table_schema='public' AND table_name='recebimento_divergencia'"
    ).fetchone()
    return bool(row)


def forward(conn) -> None:
    conn.execute("ALTER TABLE recebimento ADD COLUMN IF NOT EXISTS status_tres_vias VARCHAR(25) NOT NULL DEFAULT 'aguardando_conferencia'")
    conn.execute("ALTER TABLE recebimento ADD COLUMN IF NOT EXISTS divergencia_aprovada_por INTEGER")
    conn.execute("ALTER TABLE recebimento ADD COLUMN IF NOT EXISTS divergencia_aprovada_em TIMESTAMPTZ")
    conn.execute("ALTER TABLE recebimento ADD COLUMN IF NOT EXISTS divergencia_rejeitada_motivo TEXT")
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS recebimento_divergencia (
            id BIGSERIAL PRIMARY KEY,
            recebimento_id BIGINT NOT NULL REFERENCES recebimento(id),
            produto_id INTEGER NOT NULL,
            qtd_pedido NUMERIC(14,3),
            qtd_nf NUMERIC(14,3),
            preco_pedido NUMERIC(14,4),
            preco_nf NUMERIC(14,4),
            tipo VARCHAR(20) NOT NULL,
            dif_pct NUMERIC(8,4),
            dentro_tolerancia BOOLEAN NOT NULL DEFAULT FALSE,
            aprovada BOOLEAN NOT NULL DEFAULT FALSE,
            criado_em TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            CONSTRAINT uq_receb_diverg UNIQUE (recebimento_id, produto_id, tipo),
            CONSTRAINT chk_receb_diverg_tipo CHECK (tipo IN ('quantidade','preco','fiscal'))
        )
        """
    )
    conn.commit()


def backward(conn) -> None:
    conn.execute("DROP TABLE IF EXISTS recebimento_divergencia")
    for col in ("status_tres_vias", "divergencia_aprovada_por", "divergencia_aprovada_em", "divergencia_rejeitada_motivo"):
        conn.execute(f"ALTER TABLE recebimento DROP COLUMN IF EXISTS {col}")