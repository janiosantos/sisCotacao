"""0003 — Taxonomia: converte produtos_cadastro de texto para FKs.

Bancos antigos tinham `categoria`/`subcategoria` como colunas TEXT; a versão
normalizada usa as tabelas `categorias`/`subcategorias` com FK. A conversão usa
a técnica de rebuild de 12 passos do SQLite, preservando ids para não quebrar
referências (variantes, imagens, paginas_fonte, cotacoes).
"""
from __future__ import annotations

import sqlite3

VERSION = 3
NAME = "taxonomia normalizada (categoria/subcategoria -> FKs)"

_DDL_NEW = """
CREATE TABLE produtos_cadastro_new (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    familia_id INTEGER NOT NULL REFERENCES familias(id),
    nome TEXT NOT NULL,
    marca TEXT DEFAULT '',
    descricao TEXT DEFAULT '',
    categoria_id INTEGER REFERENCES categorias(id),
    subcategoria_id INTEGER REFERENCES subcategorias(id),
    termos_busca TEXT DEFAULT '',
    embalagem TEXT DEFAULT '',
    url TEXT DEFAULT '',
    external_id INTEGER,
    ativo INTEGER NOT NULL DEFAULT 1,
    criado_em TEXT NOT NULL DEFAULT (datetime('now')),
    atualizado_em TEXT,
    linha_produto TEXT DEFAULT '',
    classe_abc TEXT DEFAULT '',
    ordem_abc INTEGER DEFAULT 0,
    margem_lucro_estimada REAL,
    giro_esperado_mercado REAL,
    valor_agregado TEXT DEFAULT '',
    lucro_total_estimado REAL,
    em_linha INTEGER DEFAULT 1
)
"""

_SELECT_LEGACY = """
SELECT p.id, p.familia_id, p.nome, p.marca, p.descricao, p.embalagem,
       p.url, p.external_id, p.ativo, p.criado_em, p.atualizado_em,
       p.linha_produto, p.classe_abc, p.ordem_abc,
       p.margem_lucro_estimada, p.giro_esperado_mercado,
       p.valor_agregado, p.lucro_total_estimado, p.em_linha,
       c.id, sc.id, ''
FROM produtos_cadastro p
LEFT JOIN categorias c ON c.nome = TRIM(p.categoria)
LEFT JOIN subcategorias sc ON sc.nome = TRIM(p.subcategoria)
                        AND sc.categoria_id = c.id
"""


def _has_legacy_taxonomy(conn: sqlite3.Connection) -> bool:
    try:
        cols = {r[1] for r in conn.execute("PRAGMA table_info(produtos_cadastro)").fetchall()}
    except sqlite3.OperationalError:
        return False
    return "categoria" in cols and "subcategoria" in cols


def guard(conn: sqlite3.Connection) -> bool:
    """True quando o banco já está na taxonomia normalizada (nada a fazer)."""
    return not _has_legacy_taxonomy(conn)


def forward(conn: sqlite3.Connection) -> None:
    # Povoa a taxonomia antes de reconstruir (categoria -> subcategorias).
    conn.execute(
        "INSERT OR IGNORE INTO categorias (nome, ativo) "
        "SELECT TRIM(categoria), 1 FROM produtos_cadastro "
        "WHERE categoria IS NOT NULL AND TRIM(categoria) <> '' "
        "GROUP BY TRIM(categoria)"
    )
    conn.execute(
        "INSERT OR IGNORE INTO subcategorias (categoria_id, nome, ativo) "
        "SELECT c.id, TRIM(p.subcategoria), 1 "
        "FROM (SELECT DISTINCT categoria, subcategoria FROM produtos_cadastro "
        "      WHERE subcategoria IS NOT NULL AND TRIM(subcategoria) <> '') p "
        "JOIN categorias c ON c.nome = TRIM(p.categoria) "
        "GROUP BY c.id, TRIM(p.subcategoria)"
    )

    conn.execute("PRAGMA foreign_keys = OFF")
    try:
        conn.execute("BEGIN")
        conn.execute(_DDL_NEW)
        conn.execute(
            """INSERT INTO produtos_cadastro_new (
                   id, familia_id, nome, marca, descricao, embalagem, url,
                   external_id, ativo, criado_em, atualizado_em, linha_produto,
                   classe_abc, ordem_abc, margem_lucro_estimada,
                   giro_esperado_mercado, valor_agregado, lucro_total_estimado,
                   em_linha, categoria_id, subcategoria_id, termos_busca
               )
               """
            + _SELECT_LEGACY
        )
        conn.execute("DROP TABLE produtos_cadastro")
        conn.execute("ALTER TABLE produtos_cadastro_new RENAME TO produtos_cadastro")
        conn.execute("PRAGMA foreign_key_check")
        conn.execute("COMMIT")
    except sqlite3.Error:
        conn.execute("ROLLBACK")
        raise
    finally:
        conn.execute("PRAGMA foreign_keys = ON")


def backward(conn: sqlite3.Connection) -> None:
    """Rollback da normalização não é suportado (restauração via backup)."""
    raise sqlite3.OperationalError(
        "0003: rollback não suportado — restaurar via Backups/pre_3_*.db"
    )