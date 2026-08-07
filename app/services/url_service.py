from urllib.parse import urljoin
from urllib.parse import urlparse
from urllib.parse import urlunparse


class UrlService:

    @staticmethod
    def absolute(base: str, url: str) -> str:

        if not url:
            return ""

        return urljoin(base, url)

    @staticmethod
    def normalize(url: str) -> str:

        if not url:
            return ""

        parsed = urlparse(url)

        parsed = parsed._replace(
            fragment=""
        )

        return urlunparse(parsed)

    @staticmethod
    def slug(url: str):

        path = urlparse(url).path

        return path.strip("/")

    @staticmethod
    def same_domain(base, url):

        return urlparse(base).netloc == urlparse(url).netloc