"""Migração 0057 — Driver de impressora na config de impressão.

Adiciona `impressao_config.driver`: nome do driver de impressão usado pela
retaguarda. A abstração de drivers vive em `catalog_server/services/
impressao.py` (registry de drivers). O valor default `escpos_tcp` mantém o
comportamento atual (envio direto via socket TCP para host:porta).
"""
from __future__ import annotations

VERSION = 57
RISCO = "melhoria"
NAME = "impressao_driver"


def guard(conn) -> bool:
    row = conn.execute(
        "SELECT 1 FROM information_schema.columns"
        " WHERE table_name='impressao_config' AND column_name='driver'"
    ).fetchone()
    return row is not None


def forward(conn) -> None:
    autocommit = conn.autocommit
    conn.autocommit = True
    try:
        conn.execute(
            "ALTER TABLE impressao_config ADD COLUMN driver TEXT NOT NULL DEFAULT 'escpos_tcp'"
        )
    finally:
        conn.autocommit = autocommit


def backward(conn) -> None:
    autocommit = conn.autocommit
    conn.autocommit = True
    try:
        conn.execute("ALTER TABLE impressao_config DROP COLUMN IF EXISTS driver")
    finally:
        conn.autocommit = autocommit