"""Migração 0067 — JSONB canônico de atributos (ADR 0004).

Backfill idempotente do EAV (variante_atributos) para variantes.atributos
JSONB; índice GIN para busca estrutural. EAV fica congelado somente-leitura.
"""
from __future__ import annotations

VERSION = 67
RISCO = "rotina"
NAME = "jsonb_canonico"

MUDANCA = {
    "o_que": [
        "Backfill variantes.atributos a partir do EAV variante_atributos (sem sobrescrever chaves existentes)",
        "Índice GIN gin_atributos ON variantes USING gin(atributos)",
    ],
    "porque": ["JSONB é fonte canônica dos atributos (ADR 0004); EAV congelado"],
}


def guard(conn) -> bool:
    return conn.execute(
        "SELECT 1 FROM pg_indexes WHERE indexname='gin_atributos'"
    ).fetchone() is not None


def forward(conn) -> None:
    ac = conn.autocommit
    conn.autocommit = True
    try:
        conn.execute(
            """
            UPDATE variantes v SET atributos = COALESCE(v.atributos, '{}'::jsonb)
              || COALESCE((SELECT jsonb_object_agg(a.nome, av.valor)
                 FROM variante_atributos av
                 JOIN familia_atributos a ON a.id = av.atributo_id
                 WHERE av.variante_id = v.id), '{}'::jsonb)
            WHERE EXISTS (
                SELECT 1 FROM variante_atributos av2
                JOIN familia_atributos a2 ON a2.id = av2.atributo_id
                WHERE av2.variante_id = v.id
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS gin_atributos"
            " ON variantes USING gin (atributos)"
        )
    finally:
        conn.autocommit = ac


def backward(conn) -> None:
    ac = conn.autocommit
    conn.autocommit = True
    try:
        conn.execute("DROP INDEX IF EXISTS gin_atributos")
    finally:
        conn.autocommit = ac
