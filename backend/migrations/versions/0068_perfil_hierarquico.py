"""Migração 0068 — Perfil fiscal hierárquico: Produto (default) → Variação (override).

Diretiva AGENT-produtos.md #4: regra padrão no Produto; override na Variação
somente com justificativa. `fiscal_config` fica deprecado (codes = saída do
motor v2, não verdades imutáveis).
"""
from __future__ import annotations

VERSION = 68
RISCO = "rotina"
NAME = "perfil_hierarquico"

MUDANCA = {
    "o_que": [
        "Cria produto_fiscal_profile (default por produto)",
        "Adiciona justificativa_override em product_fiscal_profile (por variante)",
    ],
    "porque": [
        "Regra padrão no Produto e override na Variação somente quando justificado",
        "Codes fiscais deixam de ser verdades fixas da variação"
    ],
}


def guard(conn) -> bool:
    return conn.execute(
        "SELECT 1 FROM information_schema.tables WHERE table_name='produto_fiscal_profile'"
    ).fetchone() is not None


def forward(conn) -> None:
    ac = conn.autocommit
    conn.autocommit = True
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS produto_fiscal_profile (
                produto_id BIGINT PRIMARY KEY REFERENCES produtos_cadastro(id),
                ncm TEXT NOT NULL DEFAULT '',
                cest TEXT NOT NULL DEFAULT '',
                origem INTEGER NOT NULL DEFAULT 0,
                regime_st TEXT NOT NULL DEFAULT '',
                fonte_url TEXT,
                atualizado_em TIMESTAMP NOT NULL DEFAULT now()
            )
            """
        )
        conn.execute(
            "ALTER TABLE product_fiscal_profile"
            " ADD COLUMN IF NOT EXISTS justificativa_override TEXT NOT NULL DEFAULT ''"
        )
    finally:
        conn.autocommit = ac


def backward(conn) -> None:
    ac = conn.autocommit
    conn.autocommit = True
    try:
        conn.execute("DROP TABLE IF EXISTS produto_fiscal_profile")
        conn.execute(
            "ALTER TABLE product_fiscal_profile DROP COLUMN IF EXISTS justificativa_override"
        )
    finally:
        conn.autocommit = ac
