"""0028 - Diagnostico de variantes e ofertas duplicadas."""
from __future__ import annotations

import sqlite3

VERSION = 28
NAME = "Diagnostico de consistencia das variacoes"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS produto_diagnostico_variacao (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    produto_id      INTEGER NOT NULL UNIQUE REFERENCES produtos_cadastro(id) ON DELETE CASCADE,
    classificacao   TEXT NOT NULL CHECK(classificacao IN ('variacao_real','oferta_duplicada','cadastro_incompleto')),
    n_variantes     INTEGER NOT NULL DEFAULT 0,
    n_atributos     INTEGER NOT NULL DEFAULT 0,
    n_eans          INTEGER NOT NULL DEFAULT 0,
    observacao      TEXT NOT NULL DEFAULT '',
    revisado        INTEGER NOT NULL DEFAULT 0,
    criado_em       TEXT NOT NULL DEFAULT (datetime('now')),
    atualizado_em   TEXT
);
CREATE INDEX IF NOT EXISTS idx_diag_classificacao ON produto_diagnostico_variacao(classificacao);
CREATE INDEX IF NOT EXISTS idx_diag_revisado ON produto_diagnostico_variacao(revisado);
"""


def guard(conn: sqlite3.Connection) -> bool:
    try:
        conn.execute("SELECT 1 FROM produto_diagnostico_variacao LIMIT 1")
        return True
    except sqlite3.OperationalError:
        return False


def forward(conn: sqlite3.Connection) -> None:
    conn.executescript(_SCHEMA)
    conn.execute("DELETE FROM produto_diagnostico_variacao")
    conn.execute(
        """
        INSERT INTO produto_diagnostico_variacao
            (produto_id, classificacao, n_variantes, n_atributos, n_eans, observacao)
        SELECT produto_id,
               CASE
                 WHEN n_atributos > 0 THEN 'variacao_real'
                 WHEN n_eans > 0 AND n_eans < n_variantes THEN 'oferta_duplicada'
                 ELSE 'cadastro_incompleto'
               END,
               n_variantes, n_atributos, n_eans,
               CASE
                 WHEN n_atributos > 0 THEN 'Possui atributos de variante.'
                 WHEN n_eans > 0 AND n_eans < n_variantes THEN 'Variantes compartilham EAN; revisar como ofertas/fornecedores.'
                 ELSE 'Multiplas variantes sem atributos suficientes para montar a matriz.'
               END
        FROM (
          SELECT v.produto_id,
                 COUNT(DISTINCT v.id) AS n_variantes,
                 COUNT(DISTINCT va.id) AS n_atributos,
                 COUNT(DISTINCT CASE WHEN v.ean IS NOT NULL AND v.ean <> '' THEN v.ean END) AS n_eans
          FROM variantes v
          LEFT JOIN variante_atributos va ON va.variante_id = v.id
          WHERE v.ativo = 1
          GROUP BY v.produto_id
          HAVING COUNT(DISTINCT v.id) > 1
        )
        """
    )


def backward(conn: sqlite3.Connection) -> None:
    conn.execute("DROP TABLE IF EXISTS produto_diagnostico_variacao")
