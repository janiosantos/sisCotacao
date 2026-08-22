"""Migração 0069 — Estoque por fatos auditáveis (ADR 0003).

- estoque_movimento ganha idempotency_key UNIQUE e origem rastreável;
- quantidades migradas de DOUBLE para NUMERIC(14,3) (Regra de precisão);
- função reconciliar_saldo() compara saldo materializado × derivado.
"""
from __future__ import annotations

VERSION = 69
RISCO = "rotina"
NAME = "estoque_fatos"

MUDANCA = {
    "o_que": [
        "Adiciona idempotency_key UNIQUE e origem_tipo/origem_id em estoque_movimento",
        "Converte quantidade/reserva/saldos para NUMERIC(14,3)",
        "Cria função SQL reconciliar_estoque() (saldo derivado × materializado)",
    ],
    "porque": [
        "Estoque movimentado por fatos auditáveis com retrida segura (ADR 0003)"
    ],
}


def guard(conn) -> bool:
    return conn.execute(
        "SELECT 1 FROM information_schema.columns"
        " WHERE table_name='estoque_movimento' AND column_name='idempotency_key'"
    ).fetchone() is not None


def forward(conn) -> None:
    ac = conn.autocommit
    conn.autocommit = True
    try:
        conn.execute(
            "ALTER TABLE estoque_movimento"
            " ADD COLUMN IF NOT EXISTS idempotency_key TEXT,"
            " ADD COLUMN IF NOT EXISTS origem_tipo TEXT DEFAULT '',"
            " ADD COLUMN IF NOT EXISTS origem_id BIGINT"
        )
        conn.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS uq_emov_idempotencia"
            " ON estoque_movimento (idempotency_key)"
            " WHERE idempotency_key IS NOT NULL"
        )
        for tabela, colunas in (
            ("estoque_movimento", ("quantidade", "saldo_anterior", "saldo_posterior")),
            ("estoque_saldo", ("quantidade", "reserva", "estoque_minimo", "estoque_maximo")),
        ):
            for col in colunas:
                conn.execute(
                    f"ALTER TABLE {tabela} ALTER COLUMN {col}"
                    f" TYPE NUMERIC(14,3) USING {col}::numeric(14,3)"
                )
        conn.execute(
            """
            CREATE OR REPLACE FUNCTION reconciliar_estoque(
                p_deposito_id BIGINT, p_variante_id BIGINT
            ) RETURNS TABLE(derivado NUMERIC, materializado NUMERIC, ok BOOLEAN) AS $$
                SELECT COALESCE(SUM(CASE WHEN tipo IN ('entrada','transferencia','inventario')
                                         THEN quantidade ELSE -quantidade END), 0)::numeric(14,3),
                       (SELECT quantidade FROM estoque_saldo
                         WHERE deposito_id=p_deposito_id AND variante_id=p_variante_id),
                       COALESCE(SUM(CASE WHEN tipo IN ('entrada','transferencia','inventario')
                                         THEN quantidade ELSE -quantidade END), 0)::numeric(14,3)
                         = (SELECT quantidade FROM estoque_saldo
                             WHERE deposito_id=p_deposito_id AND variante_id=p_variante_id)
                    FROM estoque_movimento
                    WHERE deposito_id=p_deposito_id AND variante_id=p_variante_id
            $$ LANGUAGE sql
            """
        )
    finally:
        conn.autocommit = ac


def backward(conn) -> None:
    ac = conn.autocommit
    conn.autocommit = True
    try:
        conn.execute("DROP FUNCTION IF EXISTS reconciliar_estoque(BIGINT, BIGINT)")
        conn.execute("DROP INDEX IF EXISTS uq_emov_idempotencia")
        conn.execute(
            "ALTER TABLE estoque_movimento"
            " DROP COLUMN IF EXISTS idempotency_key,"
            " DROP COLUMN IF EXISTS origem_tipo, DROP COLUMN IF EXISTS origem_id"
        )
    finally:
        conn.autocommit = ac
