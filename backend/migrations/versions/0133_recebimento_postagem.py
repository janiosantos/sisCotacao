"""Migração 0133 — postagem transacional do recebimento: auditoria + reprocessamento seguro (REC-005)."""
from __future__ import annotations

VERSION = 133
RISCO = "baixa"  # Expand: tabela nova
NAME = "recebimento_postagem"

MUDANCA = {
    "o_que": [
        "Cria recebimento_postagem (registro do que foi postado: estoque, contas, total, "
        "pedido_status, contábil) para reprocessamento seguro",
    ],
    "porque": [
        "Não existe estoque sem origem, título sem recebimento ou custo sem documento; "
        "reprocessamento é seguro (REC-005)",
    ],
}


def guard(conn) -> bool:
    row = conn.execute(
        "SELECT 1 FROM information_schema.tables "
        "WHERE table_schema='public' AND table_name='recebimento_postagem'"
    ).fetchone()
    return bool(row)


def forward(conn) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS recebimento_postagem (
            id BIGSERIAL PRIMARY KEY,
            recebimento_id BIGINT NOT NULL REFERENCES recebimento(id),
            pedido_id INTEGER NOT NULL,
            estoque_itens INTEGER NOT NULL DEFAULT 0,
            contas_criadas INTEGER NOT NULL DEFAULT 0,
            total NUMERIC(16,4) NOT NULL DEFAULT 0,
            pedido_status VARCHAR(20) NOT NULL DEFAULT '',
            contabil_ok BOOLEAN NOT NULL DEFAULT FALSE,
            postado_em TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            CONSTRAINT uq_receb_postagem UNIQUE (recebimento_id)
        )
        """
    )
    conn.commit()


def backward(conn) -> None:
    conn.execute("DROP TABLE IF EXISTS recebimento_postagem")