import logging

from app.config.settings import BASE_URL, MAX_CATEGORIES

from app.core.base_crawler import BaseCrawler
from app.repositories.category_repository import CategoryRepository
from app.services.category_discovery_service import (
    CategoryDiscoveryService,
)


class CategoryCrawler(BaseCrawler):

    def __init__(self):

        super().__init__()

        self.repo = CategoryRepository()

        self.discovery = CategoryDiscoveryService()

    # ---------------------------------------------------

    def run(self) -> list:

        self.log.info("Descobrindo categorias em %s ...", BASE_URL)

        html = self.http.get(BASE_URL)

        if not html:
            self.log.error("Não foi possível acessar a home.")
            return []

        categories = self.discovery.discover(html)

        limit = MAX_CATEGORIES or None

        if limit:
            categories = categories[:limit]

        self.log.info(
            "Categorias encontradas: %s",
            len(categories),
        )

        site_to_db: dict[int, int] = {}

        pairs: list[tuple] = []

        for category in categories:

            site_id = category.id

            site_to_db[site_id] = self.repo.save(category)

            pairs.append((category, site_id))

        for category, site_id in pairs:

            parent_site_id = category.parent_id

            if parent_site_id in site_to_db:

                self.repo.update_parent(
                    site_to_db[site_id],
                    site_to_db[parent_site_id],
                )

        self.save_state("categorias", BASE_URL)

        return categories
