import logging

from app.core.base_crawler import BaseCrawler
from app.crawler.category_crawler import CategoryCrawler
from app.crawler.listing_crawler import ListingCrawler
from app.crawler.product_crawler import ProductCrawler
from app.exporters.csv_exporter import CsvExporter
from app.repositories.category_repository import CategoryRepository
from app.repositories.product_repository import ProductRepository
from app.services.category_discovery_service import (
    CategoryDiscoveryService,
)


class EcommerceCrawler(BaseCrawler):

    def __init__(self):

        super().__init__()

        self.category_crawler = CategoryCrawler()

        self.listing_crawler = ListingCrawler()

        self.product_crawler = ProductCrawler()

        self.category_repo = CategoryRepository()

        self.product_repo = ProductRepository()

        self.leafs: list = []

    # ---------------------------------------------------

    def run(self):

        self.start()

        self.stage_categories()

        self.stage_listings()

        self.stage_products()

        self.export()

        self.finish()

    # ---------------------------------------------------

    def stage_categories(self):

        self.log.info("Etapa 1/4 - Descobrindo categorias ...")

        self.category_crawler.run()

        categories = self.category_repo.list_all()

        self.leafs = CategoryDiscoveryService.leaf_categories(categories)

        self.log.info(
            "Categorias totais: %s, categorias finais (folhas): %s",
            len(categories),
            len(self.leafs),
        )

    # ---------------------------------------------------

    def stage_listings(self):

        self.log.info("Etapa 2/4 - Coletando links de produtos ...")

        for index, category in enumerate(self.leafs, start=1):

            self.log.info(
                "Listagem [%s/%s]",
                index,
                len(self.leafs),
            )

            self.listing_crawler.crawl_category(category)

        self.log.info(
            "Total de produtos registrados: %s",
            self.product_repo.count(),
        )

    # ---------------------------------------------------

    def stage_products(self):

        self.log.info("Etapa 3/4 - Processando produtos ...")

        self.product_crawler.run()

    # ---------------------------------------------------

    def export(self):

        self.log.info("Etapa 4/4 - Gerando arquivos ...")

        exporter = CsvExporter(self.product_repo)

        path = exporter.export()

        self.log.info("CSV gerado em: %s", path)
