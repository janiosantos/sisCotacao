"""0004 — cotacao_precos: +status, +moeda, renomeia desconto_percentual->desconto.

Migração Python de REBUILD (12 passos do SQLite): não dá para renomear coluna
nem adicionar CHECK/not-null-only via ALTER TABLE, então a tabela é recriada
dentro de uma transação, copiando os dados. Idempotente: se a coluna `status`
já existe, guard() retorna True e nada roda.
"""
from __future__ import annotations

import sqlite3

VERSION = 4
NAME = "cotacao_precos: status+moeda, desconto_percentual->desconto"

_DDL_NEW = """
CREATE TABLE cotacao_precos_new (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cotacao_item_id INTEGER NOT NULL REFERENCES cotacao_itens(id) ON DELETE CASCADE,
    fornecedor_id INTEGER NOT NULL REFERENCES fornecedores(id),
    preco_unitario REAL NOT NULL,
    desconto REAL,
    prazo_entrega_dias INTEGER,
    disponibilidade_estoque INTEGER NOT NULL DEFAULT 1,
    status TEXT NOT NULL DEFAULT 'pendente'
        CHECK (status IN ('pendente', 'aceito', 'recusado')),
    moeda TEXT NOT NULL DEFAULT 'BRL',
    observacao TEXT,
    registrado_em TEXT NOT NULL DEFAULT (datetime('now')),
    validade_preco_em TEXT,
    UNIQUE(cotacao_item_id, fornecedor_id)
)
"""

_INSERT_COPY = """
INSERT INTO cotacao_precos_new (
    id, cotacao_item_id, fornecedor_id, preco_unitario, desconto,
    prazo_entrega_dias, disponibilidade_estoque, status, moeda,
    observacao, registrado_em, validade_preco_em
) SELECT id, cotacao_item_id, fornecedor_id, preco_unitario,
         desconto_percentual, prazo_entrega_dias, disponibilidade_estoque,
         'pendente', 'BRL', observacao, registrado_em, validade_preco_em
FROM cotacao_precos
"""

_INDEXES_NEW = [
    "CREATE INDEX IF NOT EXISTS idx_cotacao_precos_fornecedor "
    "ON cotacao_precos(fornecedor_id)",
    "CREATE INDEX IF NOT EXISTS idx_cotacao_precos_status "
    "ON cotacao_precos(status)",
]


def guard(conn: sqlite3.Connection) -> bool:
    cols = {r[1] for r in conn.execute("PRAGMA table_info(cotacao_precos)").fetchall()}
    return "status" in cols and "desconto" in cols


def forward(conn: sqlite3.Connection) -> None:
    # 1) PRAGMA foreign_keys é no-op dentro de transação: alterna FORA.
    conn.execute("PRAGMA foreign_keys = OFF")
    try:
        conn.execute("BEGIN")  # transação explícita (runner roda em autocommit)
        conn.execute(_DDL_NEW)
        conn.execute(_INSERT_COPY)
        conn.execute("DROP TABLE cotacao_precos")
        conn.execute("ALTER TABLE cotacao_precos_new RENAME TO cotacao_precos")
        for ddl in _INDEXES_NEW:
            conn.execute(ddl)
        violacoes = conn.execute("PRAGMA foreign_key_check").fetchall()
        if violacoes:
            raise RuntimeError(f"foreign_key_check falhou: {violacoes}")
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise
    finally:
        conn.execute("PRAGMA foreign_keys = ON")


def backward(conn: sqlite3.Connection) -> None:
    """Reconstrói o formato anterior (sem status/moeda, desconto_percentual)."""
    cols = {r[1] for r in conn.execute("PRAGMA table_info(cotacao_precos)").fetchall()}
    if "status" not in cols:
        return  # já é o formato antigo; nada a fazer
    ddl_old = """
    CREATE TABLE cotacao_precos_old (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        cotacao_item_id INTEGER NOT NULL REFERENCES cotacao_itens(id) ON DELETE CASCADE,
        fornecedor_id INTEGER NOT NULL REFERENCES fornecedores(id),
        preco_unitario REAL NOT NULL,
        desconto_percentual REAL,
        prazo_entrega_dias INTEGER,
        disponibilidade_estoque INTEGER NOT NULL DEFAULT 1,
        observacao TEXT,
        registrado_em TEXT NOT NULL DEFAULT (datetime('now')),
        validade_preco_em TEXT,
        UNIQUE(cotacao_item_id, fornecedor_id)
    )
    """
    conn.execute("PRAGMA foreign_keys = OFF")
    try:
        conn.execute("BEGIN")
        conn.execute(ddl_old)
        conn.execute(
            """INSERT INTO cotacao_precos_old
                   (id, cotacao_item_id, fornecedor_id, preco_unitario,
                    desconto_percentual, prazo_entrega_dias,
                    disponibilidade_estoque, observacao, registrado_em,
                    validade_preco_em)
               SELECT id, cotacao_item_id, fornecedor_id, preco_unitario,
                      desconto, prazo_entrega_dias,
                      disponibilidade_estoque, observacao, registrado_em,
                      validade_preco_em
                 FROM cotacao_precos"""
        )
        conn.execute("DROP TABLE cotacao_precos")
        conn.execute("ALTER TABLE cotacao_precos_old RENAME TO cotacao_precos")
        conn.execute("PRAGMA foreign_key_check")
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise
    finally:
        conn.execute("PRAGMA foreign_keys = ON")