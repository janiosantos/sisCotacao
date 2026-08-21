"""Migração 0056 — Template de SKU por família.

Adiciona `familias.sku_atributos` (JSONB): lista ordenada de ids de
atributos da família que compõem o segmento de atributos do SKU estruturado
[GRUPO]-[SUBGRUPO]-[MARCA]-[ATRIBUTOS].

Quando preenchida, a geração de SKU usa apenas esses atributos, na ordem
definida (ex.: Cabo Flexível -> [bitola, cor]). Quando vazia/nula, mantém-se
o comportamento anterior (todos os atributos).
"""
from __future__ import annotations

VERSION = 56
NAME = "familia_sku_template"


def guard(conn) -> bool:
    row = conn.execute(
        "SELECT 1 FROM information_schema.columns"
        " WHERE table_name='familias' AND column_name='sku_atributos'"
    ).fetchone()
    return row is not None


def forward(conn) -> None:
    autocommit = conn.autocommit
    conn.autocommit = True
    try:
        conn.execute("ALTER TABLE familias ADD COLUMN sku_atributos JSONB")
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_familias_sku_template"
            " ON familias(id) WHERE sku_atributos IS NOT NULL"
        )
    finally:
        conn.autocommit = autocommit


def backward(conn) -> None:
    autocommit = conn.autocommit
    conn.autocommit = True
    try:
        conn.execute("ALTER TABLE familias DROP COLUMN IF EXISTS sku_atributos")
    finally:
        conn.autocommit = autocommit
