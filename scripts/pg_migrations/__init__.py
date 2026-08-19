"""Migrações versionadas do PostgreSQL (banco do catálogo/cotações).

Espelho do runner SQLite (`catalog_server.migrations`), mas aplicado ao
Postgres: o schema atual (`scripts/postgres_schema.sql`) vira a migração
`baseline` e mudanças futuras entram como arquivos `NNNN_*.sql|py` em
`versions/`, aplicados incrementalmente e registrados em `schema_migrations`.

Uso:
    python -m scripts.pg_migrations status [--url URL]
    python -m scripts.pg_migrations apply [--url URL] [--up-to N]
    python -m scripts.pg_migrations check [--url URL]
"""
from __future__ import annotations

from .runner import (
    Migration,
    MigrationError,
    apply,
    applied_versions,
    check_db,
    load_migrations,
    main as cli_main,
    status,
)

__all__ = [
    "Migration",
    "MigrationError",
    "applied_versions",
    "apply",
    "check_db",
    "cli_main",
    "load_migrations",
    "status",
]
