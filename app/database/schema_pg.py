"""Schema PostgreSQL das tabelas do scraper (espelho do crawler.db).

As tabelas (`categories`, `products`, `images`, `crawler_state` e
`product_attributes`) vivem no mesmo banco Postgres do catálogo (`DATABASE_URL`),
sem prefixo, pois não colidem com as tabelas do sistema (`categorias`,
`produtos_cadastro`, `variantes`, `imagens_produto`, ...).

O DDL é idempotente (`CREATE TABLE IF NOT EXISTS`) e é aplicado:
- pelo scraper (`app.database.sqlite.Database.create_tables`) ao abrir o banco;
- pelo `catalog_server.sync_crawler`/`enrich` antes de ler/escrever;
- pelo `scripts/migrar_postgres.py` ao importar o crawler.db.
"""
from __future__ import annotations

SCRAPER_PG_CREATE = [
    """
    CREATE TABLE IF NOT EXISTS categories(
        id BIGSERIAL PRIMARY KEY,
        parent_id INTEGER,
        name TEXT,
        slug TEXT,
        level INTEGER,
        url TEXT UNIQUE,
        breadcrumb TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS products(
        id BIGSERIAL PRIMARY KEY,
        category_id INTEGER,
        url TEXT UNIQUE,
        sku TEXT,
        ean TEXT,
        name TEXT,
        brand TEXT,
        color TEXT,
        price DOUBLE PRECISION,
        old_price DOUBLE PRECISION,
        pix_price DOUBLE PRECISION,
        installment TEXT,
        short_description TEXT,
        long_description TEXT,
        category TEXT,
        subcategory TEXT,
        downloaded INTEGER DEFAULT 0,
        parsed INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS images(
        id BIGSERIAL PRIMARY KEY,
        product_id INTEGER,
        url TEXT,
        filename TEXT,
        downloaded INTEGER DEFAULT 0
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS crawler_state(
        id INTEGER PRIMARY KEY,
        stage TEXT,
        last_url TEXT,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
]

PRODUCT_ATTRIBUTES_PG_CREATE = [
    """
    CREATE TABLE IF NOT EXISTS product_attributes (
        id BIGSERIAL PRIMARY KEY,
        product_id INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
        attr TEXT NOT NULL,
        value TEXT NOT NULL,
        UNIQUE(product_id, attr)
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_product_attributes_product"
    " ON product_attributes(product_id)",
]