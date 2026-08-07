from __future__ import annotations

import logging
import time

import requests
from fake_useragent import UserAgent


class RetryableError(Exception):
    pass


class HttpClient:

    def __init__(
        self,
        timeout: int = 30,
        max_retry: int = 3,
        user_agent: str = "",
        delay: float = 0.5,
    ):

        self.log = logging.getLogger(self.__class__.__name__)

        self.timeout = timeout
        self.max_retry = max(1, max_retry)
        self.delay = delay

        self.session = requests.Session()

        if not user_agent:

            try:
                user_agent = UserAgent().random
            except Exception:
                user_agent = (
                    "Mozilla/5.0 "
                    "(Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 "
                    "(KHTML, like Gecko) "
                    "Chrome/138.0 Safari/537.36"
                )

        self.session.headers.update(
            {
                "User-Agent": user_agent,
                "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
                "Accept": (
                    "text/html,application/xhtml+xml,"
                    "application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8"
                ),
            }
        )

    # ----------------------------------------------------------

    def _fetch(self, url: str) -> requests.Response:

        last_error: Exception | None = None

        for attempt in range(1, self.max_retry + 1):

            try:

                response = self.session.get(url, timeout=self.timeout)

                if response.status_code in (429,) or response.status_code >= 500:

                    raise RetryableError(
                        f"HTTP {response.status_code} em {url}"
                    )

                response.raise_for_status()

                return response

            except Exception as exc:

                last_error = exc

                self.log.warning(
                    "Tentativa %s/%s falhou para %s: %s",
                    attempt,
                    self.max_retry,
                    url,
                    exc,
                )

                if attempt < self.max_retry:
                    time.sleep(min(2 ** attempt, 30))

        raise last_error

    # ----------------------------------------------------------

    def get(self, url: str) -> str | None:

        try:
            response = self._fetch(url)
        except Exception as exc:
            self.log.error(
                "Falha ao buscar %s: %s",
                url,
                exc,
            )
            return None

        time.sleep(self.delay)

        return response.text

    # ----------------------------------------------------------

    def get_bytes(self, url: str) -> bytes | None:

        try:
            response = self._fetch(url)
        except Exception as exc:
            self.log.error(
                "Falha ao baixar %s: %s",
                url,
                exc,
            )
            return None

        time.sleep(self.delay)

        return response.content
