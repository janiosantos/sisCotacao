"""0006 — cotacao_itens: produto_id opcional + coluna descricao.

Permite itens de cotação "livres" (tamanho/cor não cadastrados): o produto é
informado por uma *descricao* textual (ex.: "Cabo Flexível 750V — 1,5mm² —
Amarelo") e, no momento de criar a cotação, o backend cadastra a variação no
catálogo e grava o produto_id real — assim o restante do fluxo (enriquecimento,
RFQ, comparação de preços) continua intacto.

Rebuild do SQLite (12 passos): ALTER TABLE não consegue remover NOT NULL de
`produto_id`, então a tabela é recriada numa transação copiando os dados.
Idempotente: se a coluna `descricao` já existir E `produto_id` for anulável,
guard() retorna True e nada roda.
"""
from __future__ import annotations

import sqlite3

VERSION = 6
NAME = "cotacao_itens: produto_id opcional + descricao (item livre)"

_DDL_NEW = """
CREATE TABLE cotacao_itens_new (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cotacao_id INTEGER NOT NULL REFERENCES cotacoes(id) ON DELETE CASCADE,
    produto_id INTEGER,
    descricao TEXT NOT NULL DEFAULT '',
    quantidade REAL NOT NULL DEFAULT 1,
    UNIQUE(cotacao_id, produto_id)
)
"""

_INSERT_COPY = """
INSERT INTO cotacao_itens_new (
    id, cotacao_id, produto_id, descricao, quantidade
) SELECT id, cotacao_id, produto_id, '', quantidade
  FROM cotacao_itens
"""

_INDEXES_NEW = [
    "CREATE INDEX IF NOT EXISTS idx_cotacao_itens_cotacao "
    "ON cotacao_itens(cotacao_id)",
    "CREATE INDEX IF NOT EXISTS idx_cotacao_itens_produto "
    "ON cotacao_itens(produto_id)",
]


def guard(conn: sqlite3.Connection) -> bool:
    cols = {r[1] for r in conn.execute("PRAGMA table_info(cotacao_itens)").fetchall()}
    if "descricao" not in cols:
        return False
    row = conn.execute("PRAGMA table_info(cotacao_itens)").fetchall()
    produto_nullable = any(r[1] == "produto_id" and not r[3] for r in row)
    return produto_nullable


def forward(conn: sqlite3.Connection) -> None:
    conn.execute("PRAGMA foreign_keys = OFF")
    try:
        conn.execute("BEGIN")
        conn.execute(_DDL_NEW)
        conn.execute(_INSERT_COPY)
        conn.execute("DROP TABLE cotacao_itens")
        conn.execute("ALTER TABLE cotacao_itens_new RENAME TO cotacao_itens")
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
    """Reconstrói o formato antigo: produto_id obrigatório e sem descricao."""
    cols = {r[1] for r in conn.execute("PRAGMA table_info(cotacao_itens)").fetchall()}
    if "descricao" not in cols:
        return  # já é o formato antigo; nada a fazer
    ddl_old = """
    CREATE TABLE cotacao_itens_old (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        cotacao_id INTEGER NOT NULL REFERENCES cotacoes(id) ON DELETE CASCADE,
        produto_id INTEGER NOT NULL,
        quantidade REAL NOT NULL DEFAULT 1,
        UNIQUE(cotacao_id, produto_id)
    )
    """
    conn.execute("PRAGMA foreign_keys = OFF")
    try:
        conn.execute("BEGIN")
        conn.execute(ddl_old)
        # Itens livres (produto_id NULL) não cabem no formato antigo: descartados.
        conn.execute(
            """INSERT INTO cotacao_itens_old (id, cotacao_id, produto_id, quantidade)
               SELECT id, cotacao_id, produto_id, quantidade
               FROM cotacao_itens WHERE produto_id IS NOT NULL"""
        )
        conn.execute("DROP TABLE cotacao_itens")
        conn.execute("ALTER TABLE cotacao_itens_old RENAME TO cotacao_itens")
        conn.execute("PRAGMA foreign_key_check")
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise
    finally:
        conn.execute("PRAGMA foreign_keys = ON")