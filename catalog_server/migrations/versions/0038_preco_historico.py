"""0038 - Histórico de preços (auditoria do reajuste).

`preco_historico` guarda cada alteração de preço aplicada em uma tabela:
preço anterior, novo, margem efetiva, tipo (reajuste/manual/promocao), origem e
quem aprovou (usuário da sessão). É o suporte de auditoria do módulo de
Precificação (reajuste em lote).
"""
from __future__ import annotations

import sqlite3

VERSION = 38
NAME = "Histórico de preços (auditoria)"

_SQL = """
CREATE TABLE IF NOT EXISTS preco_historico (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    tabela_id       INTEGER NOT NULL REFERENCES tabelas_preco(id) ON DELETE CASCADE,
    variante_id     INTEGER NOT NULL REFERENCES variantes(id),
    preco_anterior  REAL NOT NULL DEFAULT 0,
    preco_novo      REAL NOT NULL,
    margem_pct      REAL,
    markup_pct      REAL,
    tipo            TEXT NOT NULL DEFAULT 'reajuste'
                    CHECK(tipo IN ('reajuste','manual','promocao')),
    origem          TEXT DEFAULT '',
    usuario_id      INTEGER REFERENCES usuarios(id),
    criado_em       TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_preco_hist_tabela ON preco_historico(tabela_id);
CREATE INDEX IF NOT EXISTS idx_preco_hist_variante ON preco_historico(variante_id);
"""


def guard(conn: sqlite3.Connection) -> bool:
    try:
        conn.execute("SELECT 1 FROM preco_historico LIMIT 1").fetchone()
    except sqlite3.OperationalError:
        return False
    return True


def forward(conn: sqlite3.Connection) -> None:
    conn.executescript(_SQL)


def backward(conn: sqlite3.Connection) -> None:
    conn.execute("DROP TABLE IF EXISTS preco_historico")
