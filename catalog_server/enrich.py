"""Enriquecimento do catálogo: extrai atributos estruturados dos produtos.

Roda offline, uma única vez (ou quando novos produtos forem baixados):

    python -m catalog_server.enrich

Cria/popula a tabela `product_attributes` no banco do scraper, chamando
`grouping.extract_attributes` para cada produto `parsed=1`. Depois disso o
servidor de catálogo lê apenas os campos estruturados (nunca faz parsing dos
nomes no caminho de requisição).

Com `DATABASE_URL` configurada lê/escreve as tabelas do scraper no Postgres
(mesmo banco do sistema); senão, no `crawler.db` (SQLite).
"""
from __future__ import annotations

import sqlite3

from catalog_server.config import CATALOG_DB, DATABASE_URL
from catalog_server.grouping import FAMILY_ATTRS, extract_attributes

_SCHEMA = """
CREATE TABLE IF NOT EXISTS product_attributes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    attr TEXT NOT NULL,
    value TEXT NOT NULL,
    UNIQUE(product_id, attr)
);
CREATE INDEX IF NOT EXISTS idx_product_attributes_product
    ON product_attributes(product_id);
"""


def _enrich(conn) -> None:
    """Roda a extração de atributos usando `conn` (sqlite3 ou shim PG)."""
    rows = conn.execute("SELECT * FROM products WHERE parsed=1").fetchall()

    enriched = 0
    with_attrs = 0
    for r in rows:
        attrs = extract_attributes(dict(r))
        if not attrs.get("family"):
            continue
        enriched += 1
        pairs = {k: str(v) for k, v in attrs.items() if v}
        if len(pairs) > 1:
            with_attrs += 1
        conn.execute("DELETE FROM product_attributes WHERE product_id=?", (r["id"],))
        conn.executemany(
            "INSERT INTO product_attributes (product_id, attr, value) VALUES (?, ?, ?)",
            [(r["id"], k, v) for k, v in pairs.items()],
        )
    conn.commit()

    fams = dict(conn.execute(
        "SELECT attr, COUNT(*) FROM product_attributes WHERE attr='family' GROUP BY 1"
    ).fetchall())
    total_rows = conn.execute("SELECT COUNT(*) FROM product_attributes").fetchone()[0]

    print(f"Produtos enriquecidos: {enriched}")
    print(f"Produtos com atributos de variação: {with_attrs}")
    print(f"Linhas em product_attributes: {total_rows}")
    print("Famílias: " + ", ".join(f"{k}={v}" for k, v in fams.items()))


def run() -> None:
    if DATABASE_URL:
        from catalog_server.db import system_conn
        from app.database.schema_pg import PRODUCT_ATTRIBUTES_PG_CREATE

        with system_conn() as conn:
            for stmt in PRODUCT_ATTRIBUTES_PG_CREATE:
                conn.execute(stmt)
            conn.commit()
            _enrich(conn)
        return

    conn = sqlite3.connect(CATALOG_DB)
    conn.row_factory = sqlite3.Row
    try:
        conn.executescript(_SCHEMA)
        _enrich(conn)
    finally:
        conn.close()


if __name__ == "__main__":
    run()