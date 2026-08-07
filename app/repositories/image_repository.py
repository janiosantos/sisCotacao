from app.database.sqlite import db


class ImageRepository:

    def add(self, product_id, url, filename):

        db.execute(
            """
            INSERT INTO images
            (
                product_id,
                url,
                filename
            )
            VALUES
            (?,?,?)
            """,
            (
                product_id,
                url,
                filename,
            ),
        )

    # --------------------------------------------

    def exists(self, product_id, url):

        row = db.fetchone(
            """
            SELECT id
            FROM images
            WHERE product_id=? AND url=?
            """,
            (
                product_id,
                url,
            ),
        )

        return row is not None

    # --------------------------------------------

    def list_product(self, product_id):

        return db.fetchall(
            """
            SELECT *
            FROM images
            WHERE product_id=?
            """,
            (
                product_id,
            ),
        )

    # --------------------------------------------

    def mark_downloaded(self, image_id):

        db.execute(
            """
            UPDATE images
            SET downloaded=1
            WHERE id=?
            """,
            (
                image_id,
            ),
        )
