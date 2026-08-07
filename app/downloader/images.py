from __future__ import annotations

import hashlib
import re
from pathlib import Path
from urllib.parse import urlparse

from app.config.settings import IMAGE_FOLDER
from app.repositories.image_repository import ImageRepository
from app.services.http_client import HttpClient


class ImageDownloader:

    def __init__(self, http: HttpClient, folder: Path = IMAGE_FOLDER):

        self.http = http

        self.folder = folder

        self.repo = ImageRepository()

    # ----------------------------------------------------------

    def download(
        self,
        product_id,
        urls: list[str],
    ) -> list[str]:

        if not urls:
            return []

        destination = self.folder / str(product_id)

        destination.mkdir(parents=True, exist_ok=True)

        saved: list[str] = []

        for index, url in enumerate(urls):

            if not url:
                continue

            filename = self._filename(url, index)

            target = destination / filename

            if not target.exists():

                content = self.http.get_bytes(url)

                if content is None:
                    continue

                target.write_bytes(content)

            if not self.repo.exists(product_id, url):

                self.repo.add(product_id, url, str(target))

            saved.append(str(target))

        return saved

    # ----------------------------------------------------------

    @staticmethod
    def _filename(url: str, index: int) -> str:

        basename = Path(urlparse(url).path).name

        basename = re.sub(r"[^A-Za-z0-9._-]", "_", basename)

        if not basename:
            basename = f"imagem_{index}.jpg"

        digest = hashlib.md5(url.encode("utf-8")).hexdigest()[:8]

        stem = Path(basename).stem

        suffix = Path(basename).suffix or ".jpg"

        return f"{stem}_{digest}{suffix}"
