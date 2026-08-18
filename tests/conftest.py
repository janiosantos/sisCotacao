"""Fixtures de teste: banco SQLite temporário ou PostgreSQL (catalog_test).

Modo padrão: cada teste ganha um banco SQLite novo em arquivo temporário, com
as 52 migrations aplicadas via `catalog_server.migrations.runner.apply`.

Modo PostgreSQL (para validar a camada dual): defina `TEST_PG_URL` com a URL
do banco de teste (ex.: `postgresql+psycopg://catalog:catalog@localhost:5432/
catalog_test`). O schema é aplicado uma vez por sessão e cada teste recebe um
banco zerado via `TRUNCATE ... RESTART IDENTITY CASCADE`.
"""
from __future__ import annotations

import os

import pytest

from catalog_server import db as db_mod

TEST_PG_URL = os.getenv("TEST_PG_URL", "")


@pytest.fixture(scope="session")
def pg_schema():
    """Aplica o schema Postgres (scripts/postgres_schema.sql) uma vez por sessão."""
    if not TEST_PG_URL:
        return None
    import sqlalchemy

    engine = sqlalchemy.create_engine(TEST_PG_URL)
    schema = (
        (__import__("pathlib").Path(__file__).resolve().parent.parent / "scripts" / "postgres_schema.sql")
        .read_text(encoding="utf-8")
    )
    with engine.connect() as conn:
        conn.exec_driver_sql("DROP SCHEMA public CASCADE")
        conn.exec_driver_sql("CREATE SCHEMA public")
        for stmt in schema.split(";"):
            stmt = "\n".join(
                ln for ln in stmt.splitlines() if not ln.strip().startswith("--")
            ).strip()
            if stmt:
                conn.exec_driver_sql(stmt)
        # Seeds replicados das migrações SQLite (estado pós-migração):
        conn.exec_driver_sql("INSERT INTO depositos (nome) VALUES ('Matriz')")
        conn.exec_driver_sql("INSERT INTO tabelas_preco (nome, tipo) VALUES ('Tabela Padrão', 'varejo')")
        conn.commit()
    engine.dispose()
    return True


@pytest.fixture()
def db_path(tmp_path):
    """Cria um banco SQLite temporário com as migrations aplicadas."""
    if TEST_PG_URL:
        return None
    from catalog_server.migrations.runner import apply as apply_migrations

    path = tmp_path / "test.db"
    applied = apply_migrations(path)
    assert applied, "nenhuma migration aplicada no banco de teste"
    return path


@pytest.fixture()
def system_db(db_path, pg_schema, monkeypatch):
    """Redireciona `catalog_server.db.SYSTEM_DB` para o banco temporário.

    No modo PG, aponta `DATABASE_URL`/`_PG` para o banco de teste e zera as
    tabelas (os testes assumem banco vazio). No modo SQLite, `system_conn()`
    lê `SYSTEM_DB` do escopo do módulo `catalog_server.db` (importado por
    valor em `db.py`), então o monkeypatch precisa ser nesse módulo — e o
    cache `_MIGRATED` precisa ser limpo para o novo path.
    """
    if TEST_PG_URL:
        monkeypatch.setattr(db_mod, "DATABASE_URL", TEST_PG_URL)
        monkeypatch.setattr(db_mod, "_PG", True)
        monkeypatch.setattr(db_mod, "_MIGRATED", set())
        _truncate_all(TEST_PG_URL)
        _seed_pg(TEST_PG_URL)
        return None
    monkeypatch.setattr(db_mod, "SYSTEM_DB", db_path)
    monkeypatch.setattr(db_mod, "_MIGRATED", set())
    db_mod.init_db(db_path)
    return db_path


def _truncate_all(url: str) -> None:
    import sqlalchemy

    engine = sqlalchemy.create_engine(url)
    with engine.connect() as conn:
        tables = [
            r[0]
            for r in conn.exec_driver_sql(
                "SELECT tablename FROM pg_tables WHERE schemaname = 'public'"
            ).fetchall()
        ]
        if tables:
            conn.exec_driver_sql(
                f"TRUNCATE {', '.join(tables)} RESTART IDENTITY CASCADE"
            )
        conn.commit()
    engine.dispose()


def _seed_pg(url: str) -> None:
    import sqlalchemy

    engine = sqlalchemy.create_engine(url)
    with engine.connect() as conn:
        conn.exec_driver_sql("INSERT INTO depositos (nome) VALUES ('Matriz')")
        conn.exec_driver_sql("INSERT INTO tabelas_preco (nome, tipo) VALUES ('Tabela Padrão', 'varejo')")
        conn.commit()
    engine.dispose()


@pytest.fixture()
def conn(system_db):
    """Conexão aberta com o banco de teste (mesmo contrato do `system_conn`)."""
    with db_mod.system_conn() as c:
        yield c