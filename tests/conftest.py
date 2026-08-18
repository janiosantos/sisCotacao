"""Fixtures de teste: banco SQLite temporário com todas as migrations aplicadas.

Nenhum teste toca no `server.db` real (147 MB). Cada teste ganha um banco novo
em um arquivo temporário, com as 52 migrations aplicadas via
`catalog_server.migrations.runner.apply`.
"""
from __future__ import annotations

import pytest

from catalog_server import db as db_mod
from catalog_server.migrations.runner import apply as apply_migrations


@pytest.fixture()
def db_path(tmp_path):
    """Cria um banco SQLite temporário com as migrations aplicadas."""
    path = tmp_path / "test.db"
    applied = apply_migrations(path)
    assert applied, "nenhuma migration aplicada no banco de teste"
    return path


@pytest.fixture()
def system_db(db_path, monkeypatch):
    """Redireciona `catalog_server.db.SYSTEM_DB` para o banco temporário.

    `db.system_conn()` lê `SYSTEM_DB` do escopo do módulo `catalog_server.db`
    (importado por valor em `db.py`), então o monkeypatch precisa ser nesse
    módulo — e o cache `_MIGRATED` precisa ser limpo para o novo path.
    """
    monkeypatch.setattr(db_mod, "SYSTEM_DB", db_path)
    monkeypatch.setattr(db_mod, "_MIGRATED", set())
    db_mod.init_db(db_path)
    return db_path


@pytest.fixture()
def conn(system_db):
    """Conexão aberta com o banco de teste (mesmo contrato do `system_conn`)."""
    with db_mod.system_conn() as c:
        yield c