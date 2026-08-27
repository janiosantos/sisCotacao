"""Banco de dados do servidor de catálogo — 100% PostgreSQL.

O ERP (catálogo, fornecedores, cotações, preços, histórico, estoque, fiscal)
vive em um único banco PostgreSQL, apontado por `DATABASE_URL` (obrigatória).
O schema é evoluído por migrações versionadas em `backend/migrations/`
(contrato do `runner.py`): o `init_db` aplica as versões pendentes uma única
vez por processo e garante o índice de busca (tsvector).

O scraper (`app/`) continua local em SQLite e exporta o catálogo para JSON;
o ERP importa esse JSON e não lê o `crawler.db` diretamente.
"""
from __future__ import annotations

import os
import threading
from contextlib import contextmanager
from pathlib import Path

from catalog_server.config import DATABASE_URL


# ---------------------------------------------------------------------------
# Migrações versionadas (PostgreSQL)
# ---------------------------------------------------------------------------

_MIGRATED: set[str] = set()
_MIGRATED_LOCK = threading.Lock()


def _require_url() -> str:
    if not DATABASE_URL:
        raise RuntimeError(
            "DATABASE_URL é obrigatória: o ERP usa exclusivamente PostgreSQL. "
            "Ex.: postgresql+psycopg://usuario:senha@host:porta/banco"
        )
    return DATABASE_URL


def _ensure_migrations() -> None:
    """Aplica migrações PG pendentes uma única vez por processo/URL.

    Controlado por `AUTO_MIGRATE` (default "1"). Em produção o container roda
    com `AUTO_MIGRATE=0`: as migrações são aplicadas em passo explícito do
    pipeline (deploy.yml), fora do processo web — falha de migração não derruba
    o app em crash-loop.
    """
    url = _require_url()
    with _MIGRATED_LOCK:
        key = f"pg:{url}"
        if key in _MIGRATED:
            return
        if os.getenv("AUTO_MIGRATE", "1") != "1":
            _MIGRATED.add(key)
            return
        from migrations.runner import apply as pg_apply

        pg_apply(url)
        _MIGRATED.add(key)


def init_db() -> None:
    """Garante schema mínimo (migrações). Idempotente.

    A busca usa ILIKE + pg_trgm sobre colunas de produtos_cadastro (extensões,
    f_unaccent e índices criados pela migração 0091) — não há índice derivado a
    reconstruir.
    """
    _ensure_migrations()


@contextmanager
def system_conn():
    """Conexão com o Postgres (via shim `pgsql` que emula o contrato sqlite3).

    As migrações são garantidas uma única vez no primeiro acesso de cada
    processo (fora do hot path das requisições subsequentes).
    """
    _ensure_migrations()
    from catalog_server.pgsql import connect

    conn = connect(DATABASE_URL)
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def next_cotacao_numero(conn) -> str:
    row = conn.execute("SELECT COUNT(*) AS n FROM cotacoes").fetchone()
    return str(row["n"] + 1).zfill(4)


__all__ = [
    "system_conn",
    "init_db",
    "next_cotacao_numero",
]