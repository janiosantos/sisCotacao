"""Banco de dados do servidor de catálogo.

- Catálogo (produtos/categorias/imagens): leitura somente-leitura do banco
  gerado pelo scraper (`database/crawler.db`).
- Sistema (fornecedores, cotações, preços, histórico): banco próprio em
  SQLite com modo WAL, para suportar vários usuários na rede local.

O schema do banco de sistema é evoluído por migrações versionadas em
`catalog_server/migrations/versions/` (contrato do `runner.py`): o `init_db`
aplica as versões pendentes e espelha `schema_migrations` no `PRAGMA
user_version`. Nenhum DDL é executado no caminho de requisição (o hot path),
exceto a primeira chamada que garante as migrações.
"""
from __future__ import annotations

import sqlite3
import threading
from contextlib import contextmanager
from pathlib import Path

from catalog_server.config import CACHE_DB, SYSTEM_DB


# ---------------------------------------------------------------------------
# Migrações versionadas (system DB)
# ---------------------------------------------------------------------------

_MIGRATED: set[Path] = set()
_MIGRATED_LOCK = threading.Lock()


def _ensure_migrations(db_path: Path = SYSTEM_DB) -> None:
    """Aplica migrações pendentes uma única vez por processo/banco."""
    with _MIGRATED_LOCK:
        if db_path in _MIGRATED:
            return
        db_path.parent.mkdir(parents=True, exist_ok=True)
        from catalog_server.migrations.runner import apply

        apply(db_path)
        _MIGRATED.add(db_path)


def _ensure_ready(db_path: Path = SYSTEM_DB) -> None:
    """Alias da aplicação de migrações (um por processo)."""
    _ensure_migrations(db_path)


def init_db(db_path: Path = SYSTEM_DB) -> None:
    """Garante schema mínimo (migrações + índices FTS) para `db_path`.

    Chame no boot do servidor (e em scripts que criam o banco do zero).
    Idempotente por processo.
    """
    _ensure_ready(db_path)
    _ensure_fts(db_path)


def _ensure_fts(db_path: Path) -> None:
    from catalog_server import fts

    conn = sqlite3.connect(db_path, timeout=30)
    conn.row_factory = sqlite3.Row
    try:
        fts.ensure_fts(conn)
        if fts.is_empty(conn):
            fts.rebuild(conn)
        conn.commit()
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Cache de páginas-fonte em BANCO SEPARADO (server_cache.db)
# ---------------------------------------------------------------------------
# O HTML cru das páginas baixadas é volumoso (centenas de KB por página).
# Mantê-lo no mesmo arquivo do catálogo/ERP infla o DB e degrada o
# desempenho das consultas — por isso ele fica num banco dedicado.
CACHE_SCHEMA = """
PRAGMA journal_mode = WAL;

CREATE TABLE IF NOT EXISTS paginas_fonte (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    url TEXT NOT NULL UNIQUE,
    site TEXT DEFAULT '',
    html TEXT,
    bytes INTEGER DEFAULT 0,
    url_final TEXT DEFAULT '',
    produto_id INTEGER,
    variante_id INTEGER,
    origem TEXT DEFAULT '',
    criada_em TEXT NOT NULL DEFAULT (datetime('now')),
    atualizada_em TEXT
);
CREATE INDEX IF NOT EXISTS idx_paginas_fonte_site ON paginas_fonte(site);
CREATE INDEX IF NOT EXISTS idx_paginas_fonte_produto ON paginas_fonte(produto_id);
CREATE INDEX IF NOT EXISTS idx_paginas_fonte_variante ON paginas_fonte(variante_id);
"""


def init_cache_db() -> None:
    """Cria o banco de cache de páginas-fonte se necessário."""
    CACHE_DB.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(CACHE_DB)
    conn.executescript(CACHE_SCHEMA)
    conn.commit()
    conn.close()


@contextmanager
def cache_conn():
    """Conexão com o banco de cache de páginas-fonte (separado do catálogo)."""
    init_cache_db()
    conn = sqlite3.connect(CACHE_DB, timeout=10)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


@contextmanager
def system_conn():
    """Conexão com o banco próprio do módulo (fornecedores/cotações).

    As migrações são garantidas uma única vez no primeiro acesso de cada
    processo (fora do hot path das requisições subsequentes).
    """
    _ensure_ready(SYSTEM_DB)
    conn = sqlite3.connect(SYSTEM_DB, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def next_cotacao_numero(conn) -> str:
    row = conn.execute("SELECT COUNT(*) AS n FROM cotacoes").fetchone()
    return str(row["n"] + 1).zfill(4)


__all__ = [
    "CACHE_SCHEMA",
    "init_cache_db",
    "cache_conn",
    "system_conn",
    "init_db",
    "next_cotacao_numero",
]