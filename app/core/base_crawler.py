import logging

from app.config.settings import (
    MAX_RETRY,
    REQUEST_DELAY,
    TIMEOUT,
    USER_AGENT,
)
from app.database.sqlite import db
from app.services.http_client import HttpClient


class BaseCrawler:

    def __init__(self):

        self.log = logging.getLogger(self.__class__.__name__)

        self.http = HttpClient(
            timeout=TIMEOUT,
            max_retry=MAX_RETRY,
            user_agent=USER_AGENT,
            delay=REQUEST_DELAY,
        )

        self.db = db

    # --------------------------------------------

    def start(self):

        self.log.info("Crawler iniciado.")

    # --------------------------------------------

    def finish(self):

        self.log.info("Crawler finalizado.")

    # --------------------------------------------

    def save_state(self, stage: str, url: str):

        self.db.execute(
            """
            INSERT INTO crawler_state
            (id,stage,last_url)
            VALUES(1,?,?)
            ON CONFLICT(id)
            DO UPDATE SET
                stage=?,
                last_url=?,
                updated_at=CURRENT_TIMESTAMP
            """,
            (
                stage,
                url,
                stage,
                url,
            ),
        )

    # --------------------------------------------

    def get_state(self):

        return self.db.fetchone(
            """
            SELECT *
            FROM crawler_state
            WHERE id=1
            """
        )
