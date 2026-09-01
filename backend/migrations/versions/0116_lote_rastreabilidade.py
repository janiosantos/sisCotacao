"""Migração 0116 — rastreabilidade de lote: status, origem, custo, fornecedor,
documento, controle por família e FEFO (EST-008)."""
from __future__ import annotations

VERSION = 116
RISCO = "baixa"  # Expand: colunas novas com default; controle por família atrás de flag (DECISAO-011)
NAME = "lote_rastreabilidade"

MUDANCA = {
    "o_que": [
        "lotes + status (ativo/bloqueado), origem (compra/producao/avulsa), custo_unitario, "
        "fornecedor_id, documento, observacao",
        "familias + controle_lote (lote/série parametrizado por família — DECISAO-011)",
        "Índice por data de validade (FEFO)",
    ],
    "porque": [
        "Item controlado não entra ou sai sem rastreio; lote vencido/bloqueado não é vendido (EST-008)",
        "Recall lista clientes e documentos afetados via ledger",
    ],
}


def guard(conn) -> bool:
    row = conn.execute(
        "SELECT 1 FROM information_schema.columns "
        "WHERE table_name='lotes' AND column_name='status'"
    ).fetchone()
    return bool(row)


def forward(conn) -> None:
    conn.execute("ALTER TABLE lotes ADD COLUMN IF NOT EXISTS status VARCHAR(20) NOT NULL DEFAULT 'ativo'")
    conn.execute("ALTER TABLE lotes ADD COLUMN IF NOT EXISTS origem VARCHAR(20) NOT NULL DEFAULT 'avulsa'")
    conn.execute("ALTER TABLE lotes ADD COLUMN IF NOT EXISTS custo_unitario NUMERIC(14,4)")
    conn.execute("ALTER TABLE lotes ADD COLUMN IF NOT EXISTS fornecedor_id INTEGER")
    conn.execute("ALTER TABLE lotes ADD COLUMN IF NOT EXISTS documento VARCHAR(40)")
    conn.execute("ALTER TABLE lotes ADD COLUMN IF NOT EXISTS observacao TEXT")
    conn.execute("ALTER TABLE familias ADD COLUMN IF NOT EXISTS controle_lote BOOLEAN NOT NULL DEFAULT FALSE")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_lotes_validade ON lotes (data_validade)")
    conn.commit()


def backward(conn) -> None:
    for col in ("status", "origem", "custo_unitario", "fornecedor_id", "documento", "observacao"):
        conn.execute(f"ALTER TABLE lotes DROP COLUMN IF EXISTS {col}")
    conn.execute("ALTER TABLE familias DROP COLUMN IF EXISTS controle_lote")