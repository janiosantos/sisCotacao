"""Evolução do schema do banco de catálogo/cotações via migrações versionadas.

Pacote executável (`python -m catalog_server.migrations ...`) e biblioteca
usada pelo `db.init_db()` para aplicar versões pendentes no boot.
"""
from __future__ import annotations

from .runner import (
    Migration,
    MigrationError,
    apply,
    applied_versions,
    backup_db,
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
    "backup_db",
    "check_db",
    "cli_main",
    "load_migrations",
    "status",
]