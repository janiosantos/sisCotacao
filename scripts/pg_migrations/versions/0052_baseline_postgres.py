"""Baseline do Postgres (versão 52): o schema completo do sistema.

Aplica `scripts/postgres_schema.sql` (gerado por `schema_postgres.py` a partir
das 52 migrações SQLite) + o schema das tabelas do scraper. Numa base que já
tem o schema (ex.: banco migrado pelo `migrar_postgres.py`), o `guard` detecta
a tabela `categorias` e apenas registra a versão — idempotente.
"""
from __future__ import annotations

VERSION = 52
NAME = "baseline_postgres"


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
