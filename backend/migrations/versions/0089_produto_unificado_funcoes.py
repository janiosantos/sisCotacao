"""Migração 0089 — Unificação produto/variante (funções SQL, v2.26.0).

A migração 0087 renomeou as colunas `variante_id` -> `produto_id` nas tabelas,
mas o corpo da função SQL `reconciliar_estoque()` (criada na 0069) continuava
referenciando `variante_id`. Esta migração recria a função com o nome de coluna
correto.
"""
from __future__ import annotations

VERSION = 89
RISCO = "critica"
NAME = "produto_unificado_funcoes"

MUDANCA = {
    "o_que": [
        "CREATE OR REPLACE de reconciliar_estoque() com coluna produto_id",
    ],
    "porque": [
        "A 0087 renomeou as colunas, mas o corpo da função ficou desatualizado",
        "Consistência do modelo unificado (produto/variante)",
    ],
}


def guard(conn) -> bool:
    row = conn.execute(
        "SELECT 1 FROM pg_proc WHERE proname='reconciliar_estoque'"
        " AND NOT pg_get_functiondef(oid) ILIKE '%variante_id%'"
    ).fetchone()
    return row is not None


def forward(conn) -> None:
    ac = conn.autocommit
    conn.autocommit = True
    try:
        # CREATE OR REPLACE não permite renomear parâmetro: drop + create.
        conn.execute("DROP FUNCTION IF EXISTS reconciliar_estoque(BIGINT, BIGINT)")
        conn.execute(
            """
            CREATE FUNCTION reconciliar_estoque(
                p_deposito_id BIGINT, p_produto_id BIGINT
            ) RETURNS TABLE(derivado NUMERIC, materializado NUMERIC, ok BOOLEAN) AS $$
                SELECT COALESCE(SUM(CASE WHEN tipo IN ('entrada','transferencia','inventario')
                                         THEN quantidade ELSE -quantidade END), 0)::numeric(14,3),
                       (SELECT quantidade FROM estoque_saldo
                         WHERE deposito_id=p_deposito_id AND produto_id=p_produto_id),
                       COALESCE(SUM(CASE WHEN tipo IN ('entrada','transferencia','inventario')
                                         THEN quantidade ELSE -quantidade END), 0)::numeric(14,3)
                         = (SELECT quantidade FROM estoque_saldo
                             WHERE deposito_id=p_deposito_id AND produto_id=p_produto_id)
                    FROM estoque_movimento
                    WHERE deposito_id=p_deposito_id AND produto_id=p_produto_id
            $$ LANGUAGE sql
            """
        )
    finally:
        conn.autocommit = ac


def backward(conn) -> None:
    ac = conn.autocommit
    conn.autocommit = True
    try:
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
