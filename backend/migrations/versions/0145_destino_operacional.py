"""Migração 0145 — depósito de origem/destino dos documentos operacionais."""
from __future__ import annotations

VERSION = 145
RISCO = "rotina"
NAME = "destino_operacional"

MUDANCA = {
    "o_que": [
        "Adiciona deposito_id aos orçamentos e pedidos de compra",
        "Cria índices para consultas de demanda e trânsito por depósito",
    ],
    "porque": [
        "ABC, reposição e movimentações não podem usar sempre o depósito 1",
        "O destino precisa acompanhar o documento durante todo o ciclo",
    ],
}


def guard(conn) -> bool:
    rows = conn.execute(
        "SELECT table_name, column_name FROM information_schema.columns "
        "WHERE table_schema='public' AND column_name='deposito_id' "
        "AND table_name IN ('orcamentos','pedidos_compra')"
    ).fetchall()
    return len(rows) == 2


def forward(conn) -> None:
    conn.execute("ALTER TABLE orcamentos ADD COLUMN IF NOT EXISTS deposito_id INTEGER")
    conn.execute("ALTER TABLE pedidos_compra ADD COLUMN IF NOT EXISTS deposito_id INTEGER")
    conn.execute(
        "UPDATE pedidos_compra pc SET deposito_id=sc.deposito_id "
        "FROM cotacoes c JOIN solicitacao_compra sc ON sc.id=c.solicitacao_id "
        "WHERE pc.cotacao_id=c.id AND pc.deposito_id IS NULL"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS ix_orcamentos_deposito_criado "
        "ON orcamentos (deposito_id, criado_em)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS ix_pedidos_compra_deposito_status "
        "ON pedidos_compra (deposito_id, status)"
    )
    conn.commit()


def backward(conn) -> None:
    conn.execute("DROP INDEX IF EXISTS ix_pedidos_compra_deposito_status")
    conn.execute("DROP INDEX IF EXISTS ix_orcamentos_deposito_criado")
    conn.execute("ALTER TABLE pedidos_compra DROP COLUMN IF EXISTS deposito_id")
    conn.execute("ALTER TABLE orcamentos DROP COLUMN IF EXISTS deposito_id")
