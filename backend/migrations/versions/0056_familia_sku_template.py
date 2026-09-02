"""Migração 0056 — Template de SKU por família.

Adiciona `familias.sku_atributos` (JSONB): lista ordenada de atributos usados
na identificação e pesquisa das variações. O SKU de acesso rápido não carrega
esses valores; ele usa `[GRUPO]-[SUBGRUPO]-[FAM][-VAR]`.

Quando preenchida, a interface usa apenas esses atributos, na ordem definida
para descrever e localizar variações (ex.: Cabo Flexível -> [bitola, cor]).
"""
from __future__ import annotations

VERSION = 56
RISCO = "melhoria"

# Documentação da mudança de banco (exigida pelo runner desde a v1.6.2).
MUDANCA = {
    "o_que": ["Adiciona familias.sku_atributos (JSONB)"],
    "porque": [
        "Define quais atributos da família ajudam a descrever e localizar as variações, na ordem",
    ],
}
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
