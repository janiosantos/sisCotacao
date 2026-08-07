from __future__ import annotations

from typing import Optional

from app.database.sqlite import db
from app.models.category import Category


class CategoryRepository:

    def save(self, category: Category) -> int:

        existing = self.find_by_url(category.url)

        if existing:
            category.id = existing.id
            return existing.id

        category.id = db.insert(
            """
            INSERT INTO categories
            (
                parent_id,
                name,
                slug,
                level,
                url,
                breadcrumb
            )
            VALUES
            (
                ?,?,?,?,?,?
            )
            """,
            (
                category.parent_id,
                category.name,
                category.slug,
                category.level,
                category.url,
                category.breadcrumb,
            ),
        )

        return category.id

    # ------------------------------------------------------

    def update_parent(
        self,
        category_id: int,
        parent_id: Optional[int],
    ):

        db.execute(
            """
            UPDATE categories
            SET parent_id=?
            WHERE id=?
            """,
            (
                parent_id,
                category_id,
            ),
        )

    # ------------------------------------------------------

    def find_by_url(
        self,
        url: str,
    ) -> Optional[Category]:

        row = db.fetchone(
            """
            SELECT *
            FROM categories
            WHERE url=?
            """,
            (
                url,
            ),
        )

        if row is None:
            return None

        return Category(
            id=row["id"],
            parent_id=row["parent_id"],
            level=row["level"],
            name=row["name"],
            slug=row["slug"],
            breadcrumb=row["breadcrumb"],
            url=row["url"],
        )

    # ------------------------------------------------------

    def list_all(self):

        rows = db.fetchall(
            """
            SELECT *
            FROM categories
            ORDER BY level,name
            """
        )

        return [
            Category(
                id=row["id"],
                parent_id=row["parent_id"],
                level=row["level"],
                name=row["name"],
                slug=row["slug"],
                breadcrumb=row["breadcrumb"],
                url=row["url"],
            )
            for row in rows
        ]

    # ------------------------------------------------------

    def count(self):

        row = db.fetchone(
            """
            SELECT COUNT(*) total
            FROM categories
            """
        )

        return row["total"]

    # ------------------------------------------------------

    def delete_all(self):

        db.execute(
            """
            DELETE FROM categories
            """
        )