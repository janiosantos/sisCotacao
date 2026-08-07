from __future__ import annotations

from typing import Optional

from app.database.sqlite import db
from app.models.product import Product


class ProductRepository:

    def save_stub(
        self,
        url: str,
        name: str,
        category_id: Optional[int],
        category: str,
        subcategory: str,
    ) -> int:

        existing = self.find_by_url(url)

        if existing:
            return existing.id

        return db.insert(
            """
            INSERT INTO products
            (
                category_id,
                url,
                name,
                category,
                subcategory
            )
            VALUES
            (?,?,?,?,?)
            """,
            (
                category_id,
                url,
                name,
                category,
                subcategory,
            ),
        )

    # -------------------------------------------------

    def update(self, product: Product):

        db.execute(
            """
            UPDATE products
            SET
                sku=?,
                ean=?,
                name=?,
                brand=?,
                color=?,
                price=?,
                old_price=?,
                pix_price=?,
                installment=?,
                short_description=?,
                long_description=?,
                category=?,
                subcategory=?,
                parsed=1
            WHERE id=?
            """,
            (
                product.sku,
                product.ean,
                product.name,
                product.brand,
                product.color,
                product.price,
                product.old_price,
                product.pix_price,
                product.installment,
                product.short_description,
                product.long_description,
                product.category,
                product.subcategory,
                product.id,
            ),
        )

    # -------------------------------------------------

    def find_by_url(self, url: str) -> Optional[Product]:

        row = db.fetchone(
            """
            SELECT *
            FROM products
            WHERE url=?
            """,
            (
                url,
            ),
        )

        if row is None:
            return None

        return self._row_to_product(row)

    # -------------------------------------------------

    def pending(self) -> list[Product]:

        rows = db.fetchall(
            """
            SELECT *
            FROM products
            WHERE parsed=0
            ORDER BY id
            """
        )

        return [self._row_to_product(r) for r in rows]

    # -------------------------------------------------

    def pending_count(self) -> int:

        row = db.fetchone(
            """
            SELECT COUNT(*) total
            FROM products
            WHERE parsed=0
            """
        )

        return row["total"]

    # -------------------------------------------------

    def mark_downloaded(self, product_id):

        db.execute(
            """
            UPDATE products
            SET downloaded=1
            WHERE id=?
            """,
            (
                product_id,
            ),
        )

    # -------------------------------------------------

    def export_rows(self) -> list[dict]:

        rows = db.fetchall(
            """
            SELECT p.*,
                   COALESCE(
                       (SELECT GROUP_CONCAT(i.url, '|')
                        FROM images i
                        WHERE i.product_id = p.id),
                       ''
                   ) AS image_urls,
                   COALESCE(
                       (SELECT GROUP_CONCAT(i.filename, '|')
                        FROM images i
                        WHERE i.product_id = p.id),
                       ''
                   ) AS image_files
            FROM products p
            WHERE p.parsed=1
            ORDER BY p.category, p.subcategory, p.name
            """
        )

        return [dict(r) for r in rows]

    # -------------------------------------------------

    def count(self) -> int:

        row = db.fetchone(
            """
            SELECT COUNT(*) total
            FROM products
            """
        )

        return row["total"]

    # -------------------------------------------------

    @staticmethod
    def _row_to_product(row) -> Product:

        return Product(
            id=row["id"],
            category_id=row["category_id"],
            url=row["url"] or "",
            sku=row["sku"] or "",
            ean=row["ean"] or "",
            name=row["name"] or "",
            brand=row["brand"] or "",
            color=row["color"] or "",
            price=row["price"] or 0.0,
            old_price=row["old_price"],
            pix_price=row["pix_price"] or 0.0,
            installment=row["installment"] or "",
            short_description=row["short_description"] or "",
            long_description=row["long_description"] or "",
            category=row["category"] or "",
            subcategory=row["subcategory"] or "",
        )
