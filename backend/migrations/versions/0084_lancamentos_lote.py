"""Migração 0084 — Lançamentos parcelados, recorrentes e com origem (v2.25.0).

Modelo TOTVS (desdobramento FINA050/FINA040):
- 1 lançamento gera N títulos (parcelas) com vencimentos diferenciados, por
  condição de pagamento, intervalo manual ou datas explícitas.
- Recorrência (aluguel/mensalidade): todas as ocorrências geradas antecipadas.
- Origem rastreável: pedido de compra (contas a pagar) e venda (contas a
  receber) vinculados ao título.

Expand-only. Backfill: títulos existentes viram `manual`, parcela 1/1.
"""
from __future__ import annotations

VERSION = 84
RISCO = "moderada"
NAME = "lancamentos_lote"

MUDANCA = {
    "o_que": [
        "contas_pagar e contas_receber: colunas origem_tipo, origem_id, parcela, total_parcelas, grupo_id, recorrencia",
        "Tabela conta_anexo (documento/boleto/comprovante anexado ao lançamento)",
        "Backfill: origem_tipo='manual', parcela=1, total_parcelas=1 nos títulos existentes",
        "Índice em grupo_id (pagar e receber)",
    ],
    "porque": [
        "Compra parcelada 30/60/90 exigia N lançamentos manuais — agora 1 lançamento gera todas as parcelas (modelo TOTVS)",
        "Recorrência (aluguel/mensalidade) e origem do débito/crédito não existiam",
    ],
}


def guard(conn) -> bool:
    row = conn.execute(
        "SELECT 1 FROM information_schema.columns"
        " WHERE table_name='contas_pagar' AND column_name='grupo_id'"
    ).fetchone()
    return row is not None


def forward(conn) -> None:
    ac = conn.autocommit
    conn.autocommit = True
    try:
        for tabela in ("contas_pagar", "contas_receber"):
            conn.execute(
                f"ALTER TABLE {tabela}"
                " ADD COLUMN IF NOT EXISTS origem_tipo TEXT DEFAULT 'manual'"
            )
            conn.execute(
                f"ALTER TABLE {tabela}"
                " ADD COLUMN IF NOT EXISTS origem_id BIGINT"
            )
            conn.execute(
                f"ALTER TABLE {tabela}"
                " ADD COLUMN IF NOT EXISTS parcela INTEGER NOT NULL DEFAULT 1"
            )
            conn.execute(
                f"ALTER TABLE {tabela}"
                " ADD COLUMN IF NOT EXISTS total_parcelas INTEGER NOT NULL DEFAULT 1"
            )
            conn.execute(
                f"ALTER TABLE {tabela}"
                " ADD COLUMN IF NOT EXISTS grupo_id TEXT DEFAULT ''"
            )
            conn.execute(
                f"ALTER TABLE {tabela}"
                " ADD COLUMN IF NOT EXISTS recorrencia TEXT DEFAULT ''"
            )
            conn.execute(
                f"CREATE INDEX IF NOT EXISTS idx_{tabela}_grupo ON {tabela} (grupo_id)"
            )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS conta_anexo (
                id          BIGSERIAL PRIMARY KEY,
                tabela      TEXT NOT NULL DEFAULT 'pagar',
                conta_id    BIGINT NOT NULL,
                tipo        TEXT NOT NULL DEFAULT 'documento',
                filename    TEXT NOT NULL,
                descricao   TEXT NOT NULL DEFAULT '',
                usuario_id  BIGINT REFERENCES usuarios(id),
                criado_em   TEXT NOT NULL DEFAULT (to_char(now(),'YYYY-MM-DD HH24:MI:SS'))
            )
            """
        )
        conn.execute(
            "UPDATE contas_pagar SET origem_tipo='manual'"
            " WHERE origem_tipo IS NULL OR origem_tipo=''"
        )
        conn.execute(
            "UPDATE contas_receber SET origem_tipo='manual'"
            " WHERE origem_tipo IS NULL OR origem_tipo=''"
        )
    finally:
        conn.autocommit = ac


def backward(conn) -> None:
    ac = conn.autocommit
    conn.autocommit = True
    try:
        conn.execute("DROP TABLE IF EXISTS conta_anexo")
        for tabela in ("contas_pagar", "contas_receber"):
            conn.execute(f"DROP INDEX IF EXISTS idx_{tabela}_grupo")
            conn.execute(f"ALTER TABLE {tabela} DROP COLUMN IF EXISTS recorrencia")
            conn.execute(f"ALTER TABLE {tabela} DROP COLUMN IF EXISTS grupo_id")
            conn.execute(f"ALTER TABLE {tabela} DROP COLUMN IF EXISTS total_parcelas")
            conn.execute(f"ALTER TABLE {tabela} DROP COLUMN IF EXISTS parcela")
            conn.execute(f"ALTER TABLE {tabela} DROP COLUMN IF EXISTS origem_id")
            conn.execute(f"ALTER TABLE {tabela} DROP COLUMN IF EXISTS origem_tipo")
    finally:
        conn.autocommit = ac