"""Regressoes da migration que repara a fila de impressao."""
from __future__ import annotations

from catalog_server.db import system_conn
from migrations.runner import MIGRATIONS_DIR, Migration


def test_migration_recria_fila_ausente_sem_perder_config(system_db):
    migration = Migration(MIGRATIONS_DIR / "0156_reparo_fila_impressao.py")
    with system_conn() as conn:
        conn.execute(
            "INSERT INTO impressao_config (id, host, porta) VALUES (1, '10.0.0.9', 9100)"
        )
        conn.execute("DROP TABLE impressao_fila")
        conn.commit()

        assert migration.guard(conn) is False
        migration.forward(conn)
        assert migration.guard(conn) is True

        config = conn.execute(
            "SELECT host, porta FROM impressao_config WHERE id=1"
        ).fetchone()
        assert config["host"] == "10.0.0.9"
        assert config["porta"] == 9100

        job = conn.execute(
            "INSERT INTO impressao_fila (payload) VALUES ('{}') RETURNING id"
        ).fetchone()
        assert job["id"] > 0
