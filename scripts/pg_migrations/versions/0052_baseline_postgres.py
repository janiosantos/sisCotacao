"""Baseline do Postgres (versão 52): o schema completo do sistema.

Aplica `scripts/postgres_schema.sql` (schema de referência do ERP) + o schema
das tabelas do scraper. Numa base que já tem o schema, o `guard` detecta a
tabela `categorias` e apenas registra a versão — idempotente.
"""
from __future__ import annotations

VERSION = 52
NAME = "baseline_postgres"
RISCO = "critica"

# Documentação da mudança de banco (exigida pelo runner desde a v1.6.2).
MUDANCA = {
    "o_que": ["Cria o schema completo do ERP no Postgres a partir de scripts/postgres_schema.sql"],
    "porque": ["Migração do armazenamento local para banco único PostgreSQL"],
}


def _schema_statements():
    from scripts.pg_migrations.runner import SCHEMA_FILE

    return SCHEMA_FILE.read_text(encoding="utf-8")


def guard(conn) -> bool:
    row = conn.execute(
        "SELECT 1 FROM information_schema.tables"
        " WHERE table_schema = 'public' AND table_name = 'categorias'"
    ).fetchone()
    return row is not None


def forward(conn) -> None:
    from app.database.schema_pg import PRODUCT_ATTRIBUTES_PG_CREATE, SCRAPER_PG_CREATE

    autocommit = conn.autocommit
    conn.autocommit = True
    try:
        conn.execute(_schema_statements())
        for stmt in SCRAPER_PG_CREATE + PRODUCT_ATTRIBUTES_PG_CREATE:
            conn.execute(stmt)
    finally:
        conn.autocommit = autocommit
