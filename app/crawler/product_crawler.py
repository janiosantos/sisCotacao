import logging

from app.config.settings import DOWNLOAD_IMAGES, MAX_PRODUCTS
from app.core.base_crawler import BaseCrawler
from app.downloader.images import ImageDownloader
from app.models.product import Product
from app.parsers.product_parser import ProductParser
from app.repositories.product_repository import ProductRepository


class ProductCrawler(BaseCrawler):

    def __init__(self):

        super().__init__()

        self.parser = ProductParser()

        self.repo = ProductRepository()

        self.downloader = ImageDownloader(self.http)

    # ---------------------------------------------------

    def run(self) -> int:

        pending = self.repo.pending()

        total = len(pending)

        limit = MAX_PRODUCTS or total

        pending = pending[:limit]

        self.log.info(
            "Produtos pendentes: %s (processando %s)",
            total,
            len(pending),
        )

        processed = 0
        failed = 0

        for index, product in enumerate(pending, start=1):

            ok = self.crawl(product)

            if ok:
                processed += 1
            else:
                failed += 1

            if index % 50 == 0 or index == len(pending):

                self.log.info(
                    "Progresso: %s/%s produtos.",
                    index,
                    len(pending),
                )

        self.log.info(
            "Produtos processados: %s, falhas: %s.",
            processed,
            failed,
        )

        return processed

    # ---------------------------------------------------

    def crawl(self, product: Product) -> bool:

        self.log.info(
            "Processando produto %s: %s",
            product.id,
            product.name,
        )

        html = self.http.get(product.url)

        if not html:
            return False

        data = self.parser.parse(html, url=product.url)

        self._apply(product, data)

        if DOWNLOAD_IMAGES:

            files = self.downloader.download(product.id, data["images"])

            product.image_files = files

        self.repo.update(product)

        return True

    # ---------------------------------------------------

    @staticmethod
    def _apply(product: Product, data: dict):

        product.sku = data.get("sku") or ""
        product.ean = data.get("ean") or ""
        product.name = data.get("name") or product.name
        product.brand = data.get("brand") or ""
        product.color = data.get("color") or ""
        product.price = data.get("price") or 0.0
        product.old_price = data.get("old_price")
        product.pix_price = data.get("pix_price") or 0.0
        product.installment = data.get("installment") or ""
        product.short_description = data.get("short_description") or ""
        product.long_description = data.get("long_description") or ""
        product.images = data.get("images") or []
