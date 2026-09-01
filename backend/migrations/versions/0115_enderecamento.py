"""Migração 0115 — endereçamento: posições de armazenagem, saldo por posição e log de movimentação (EST-007)."""
from __future__ import annotations

VERSION = 115
RISCO = "baixa"  # Expand: tabelas novas
NAME = "enderecamento"

MUDANCA = {
    "o_que": [
        "Cria endereco_posicao (posições rua-módulo-posição-nível por depósito), "
        "endereco_estoque (saldo por posição, com posição primária) e "
        "endereco_movimento (log de entrada/saída/movimentação entre endereços)",
    ],
    "porque": [
        "Otimiza separação por endereço; movimentação de endereço é registrada (EST-007)",
        "Produto tem posição primária (e secundárias) por depósito",
    ],
}


def guard(conn) -> bool:
    row = conn.execute(
        "SELECT 1 FROM information_schema.tables "
        "WHERE table_schema='public' AND table_name='endereco_posicao'"
    ).fetchone()
    return bool(row)


def forward(conn) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS endereco_posicao (
            id BIGSERIAL PRIMARY KEY,
            deposito_id INTEGER NOT NULL,
            codigo VARCHAR(40) NOT NULL,
            ativo BOOLEAN NOT NULL DEFAULT TRUE,
            criado_em TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            CONSTRAINT uq_endereco_codigo UNIQUE (deposito_id, codigo)
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS endereco_estoque (
            id BIGSERIAL PRIMARY KEY,
            posicao_id BIGINT NOT NULL REFERENCES endereco_posicao(id),
            produto_id INTEGER NOT NULL,
            quantidade NUMERIC(14,3) NOT NULL DEFAULT 0,
            primaria BOOLEAN NOT NULL DEFAULT FALSE,
            CONSTRAINT uq_endereco_estoque UNIQUE (posicao_id, produto_id)
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS endereco_movimento (
            id BIGSERIAL PRIMARY KEY,
            posicao_id BIGINT NOT NULL REFERENCES endereco_posicao(id),
            produto_id INTEGER NOT NULL,
            tipo VARCHAR(15) NOT NULL,  -- entrada | saida | movimentacao
            quantidade NUMERIC(14,3) NOT NULL,
            usuario_id INTEGER,
            criado_em TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            CONSTRAINT chk_endereco_mov_tipo CHECK (tipo IN ('entrada','saida','movimentacao'))
        )
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_endereco_estoque_produto ON endereco_estoque (produto_id)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_endereco_mov_posicao ON endereco_movimento (posicao_id)"
    )
    conn.commit()


def backward(conn) -> None:
    for t in ("endereco_movimento", "endereco_estoque", "endereco_posicao"):
        conn.execute(f"DROP TABLE IF EXISTS {t}")