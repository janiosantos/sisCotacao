from __future__ import annotations

import sqlite3

from app.config.settings import DATABASE_FOLDER


class Database:

    def __init__(self):

        self.db_path = DATABASE_FOLDER / "crawler.db"

        # O scraper é uma aplicação 100% local (SQLite). O ERP consome os
        # produtos por arquivo de exportação (JSON), não por este banco.
        self.is_pg = False

        self.conn = sqlite3.connect(
            self.db_path,
            check_same_thread=False
        )

        self.conn.row_factory = sqlite3.Row

        self.create_tables()

        self.migrate()

    # --------------------------------------------------

    def create_tables(self):

        cursor = self.conn.cursor()

        cursor.execute("""

        CREATE TABLE IF NOT EXISTS categories(

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            parent_id INTEGER,

            name TEXT,

            slug TEXT,

            level INTEGER,

            url TEXT UNIQUE,

            breadcrumb TEXT,

            created_at DATETIME DEFAULT CURRENT_TIMESTAMP

        )

        """)

        cursor.execute("""

        CREATE TABLE IF NOT EXISTS products(

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            category_id INTEGER,

            url TEXT UNIQUE,

            sku TEXT,

            ean TEXT,

            name TEXT,

            brand TEXT,

            color TEXT,

            price REAL,

            old_price REAL,

            pix_price REAL,

            installment TEXT,

            short_description TEXT,

            long_description TEXT,

            category TEXT,

            subcategory TEXT,

            downloaded INTEGER DEFAULT 0,

            parsed INTEGER DEFAULT 0,

            created_at DATETIME DEFAULT CURRENT_TIMESTAMP

        )

        """)

        cursor.execute("""

        CREATE TABLE IF NOT EXISTS images(

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            product_id INTEGER,

            url TEXT,

            filename TEXT,

            downloaded INTEGER DEFAULT 0

        )

        """)

        cursor.execute("""

        CREATE TABLE IF NOT EXISTS crawler_state(

            id INTEGER PRIMARY KEY,

            stage TEXT,

            last_url TEXT,

            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP

        )

        """)

        self.conn.commit()

    # --------------------------------------------------

    def _ensure_column(
        self,
        table: str,
        column: str,
        definition: str,
    ):

        columns = {
            row["name"]
            for row in self.fetchall(
                f"PRAGMA table_info({table})"
            )
        }

        if column not in columns:

            self.execute(
                f"ALTER TABLE {table} ADD COLUMN {column} {definition}"
            )

    # --------------------------------------------------

    def migrate(self):

        self._ensure_column(
            "products",
            "old_price",
            "REAL",
        )

        self._ensure_column(
            "products",
            "category",
            "TEXT",
        )

        self._ensure_column(
            "products",
            "subcategory",
            "TEXT",
        )

    # --------------------------------------------------

    def execute(self, sql, values=None):

        if values:

            cur = self.conn.execute(sql, values)

        else:

            cur = self.conn.execute(sql)

        self.conn.commit()

        return cur

    # --------------------------------------------------

    def fetchone(self, sql, values=None):

        cur = self.execute(sql, values)

        return cur.fetchone()

    # --------------------------------------------------

    def fetchall(self, sql, values=None):

        cur = self.execute(sql, values)

        return cur.fetchall()

    # --------------------------------------------------

    def close(self):

        self.conn.close()

    # --------------------------------------------------

    def insert(self, sql, values):

        cursor = self.conn.execute(sql, values)

        self.conn.commit()

        return cursor.lastrowid

    # --------------------------------------------------

    def executemany(self, sql, values):

        self.conn.executemany(sql, values)

        self.conn.commit()


db = Database()