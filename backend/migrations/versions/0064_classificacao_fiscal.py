"""Migração 0064 — Classificação fiscal: NCM/CEST versionados e perfil fiscal do produto.

Separa cadastro comercial de perfil fiscal (skill fiscal-mg §4):
- ncm_version / cest_version com vigência e fonte oficial;
- product_fiscal_profile por VARIANTE (NCM, CEST, origem independente).
Nenhum código de NCM/CEST é semeado aqui — entrada somente via fontes oficiais.
"""
from __future__ import annotations

VERSION = 64
RISCO = "rotina"
NAME = "classificacao_fiscal"

# Documentação da mudança de banco (exigida pelo runner desde a v1.6.2).
MUDANCA = {
    "o_que": [
        "Cria ncm_version e cest_version (código + descrição + vigência + fonte_url)",
        "Cria product_fiscal_profile por variante (ncm, cest, origem, regime_st, fonte_url)",
    ],
    "porque": [
        "Separar perfil fiscal do cadastro comercial: NCM não determina sozinho ST/CFOP/CST/CSOSN",
        "Classificação versionada com fonte/vigência para auditoria (ADR 0001)",
    ],
}


def guard(conn) -> bool:
    row = conn.execute(
        "SELECT 1 FROM information_schema.tables"
        " WHERE table_name='product_fiscal_profile'"
    ).fetchone()
    return row is not None


def forward(conn) -> None:
    autocommit = conn.autocommit
    conn.autocommit = True
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS ncm_version (
                id BIGSERIAL PRIMARY KEY,
                codigo TEXT NOT NULL,
                descricao TEXT NOT NULL DEFAULT '',
                vigencia_inicio DATE,
                vigencia_fim DATE,
                fonte_url TEXT,
                criado_em TIMESTAMP NOT NULL DEFAULT now(),
                UNIQUE (codigo, vigencia_inicio)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS cest_version (
                id BIGSERIAL PRIMARY KEY,
                codigo TEXT NOT NULL,
                descricao TEXT NOT NULL DEFAULT '',
                ncm_padrao TEXT NOT NULL DEFAULT '',
                segmento TEXT NOT NULL DEFAULT '',
                vigencia_inicio DATE,
                vigencia_fim DATE,
                fonte_url TEXT,
                criado_em TIMESTAMP NOT NULL DEFAULT now(),
                UNIQUE (codigo, vigencia_inicio)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS product_fiscal_profile (
                variante_id BIGINT PRIMARY KEY REFERENCES variantes(id),
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
            "CREATE INDEX IF NOT EXISTS idx_pfp_ncm ON product_fiscal_profile (ncm)"
        )
    finally:
        conn.autocommit = autocommit


def backward(conn) -> None:
    autocommit = conn.autocommit
    conn.autocommit = True
    try:
        for tabela in ("product_fiscal_profile", "cest_version", "ncm_version"):
            conn.execute(f"DROP TABLE IF EXISTS {tabela}")
    finally:
        conn.autocommit = autocommit
