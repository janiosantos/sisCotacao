"""0005 — Índices operacionais do catálogo (_INDEXES + drop do legado).

O antigo `db._ensure_indexes` criava estes índices fora do schema estático.
Bancos que chegarem ao runner sem eles (criados antes desse conjunto) recebem
aqui, idempotente via CREATE INDEX IF NOT EXISTS.
"""
from __future__ import annotations

import re
import sqlite3

VERSION = 5
NAME = "índices operacionais do catálogo"

_IDX_NAME = re.compile(r"CREATE INDEX IF NOT EXISTS\s+(\S+)\s+ON")

_INDEXES = [
    "DROP INDEX IF EXISTS idx_variantes_ativo",
    "CREATE INDEX IF NOT EXISTS idx_produtos_nome ON produtos_cadastro(nome COLLATE NOCASE)",
    "CREATE INDEX IF NOT EXISTS idx_produtos_familia ON produtos_cadastro(familia_id)",
    "CREATE INDEX IF NOT EXISTS idx_produtos_categoria_id ON produtos_cadastro(categoria_id)",
    "CREATE INDEX IF NOT EXISTS idx_produtos_subcategoria_id ON produtos_cadastro(subcategoria_id)",
    "CREATE INDEX IF NOT EXISTS idx_produtos_linha ON produtos_cadastro(linha_produto)",
    "CREATE INDEX IF NOT EXISTS idx_produtos_classe_abc ON produtos_cadastro(classe_abc)",
    "CREATE INDEX IF NOT EXISTS idx_produtos_ordem_abc ON produtos_cadastro(ordem_abc)",
    "CREATE INDEX IF NOT EXISTS idx_produtos_em_linha ON produtos_cadastro(em_linha)",
    "CREATE INDEX IF NOT EXISTS idx_produtos_ativo ON produtos_cadastro(ativo)",
    "CREATE INDEX IF NOT EXISTS idx_variantes_produto ON variantes(produto_id)",
    "CREATE INDEX IF NOT EXISTS idx_variantes_produto_ativo ON variantes(produto_id, ativo)",
    "CREATE INDEX IF NOT EXISTS idx_imagens_produto_produto ON imagens_produto(produto_id)",
    "CREATE INDEX IF NOT EXISTS idx_variante_atributos_variante ON variante_atributos(variante_id)",
    "CREATE INDEX IF NOT EXISTS idx_variante_atributos_atributo ON variante_atributos(atributo_id)",
    "CREATE INDEX IF NOT EXISTS idx_familia_atributos_familia ON familia_atributos(familia_id)",
]


def guard(conn: sqlite3.Connection) -> bool:
    rows = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='index' AND name NOT LIKE 'sqlite_%'"
    ).fetchall()
    have = {r[0] for r in rows}
    needed = {m.group(1) for d in _INDEXES if (m := _IDX_NAME.search(d))}
    return all(i in have for i in needed)


def forward(conn: sqlite3.Connection) -> None:
    for stmt in _INDEXES:
        conn.execute(stmt)