from app.core.base_crawler import BaseCrawler
from app.models.category import Category
from app.parsers.listing_parser import ListingParser
from app.repositories.product_repository import ProductRepository


class ListingCrawler(BaseCrawler):

    def __init__(self):

        super().__init__()

        self.parser = ListingParser()

        self.repo = ProductRepository()

    # ---------------------------------------------------

    def crawl_category(self, category: Category) -> int:

        total_found = 0

        html = self.http.get(category.url)

        if not html:
            return 0

        page_urls = self.parser.parse_pagination(html, category.url)

        category_name, subcategory_name = self._names(category)

        for index, page_url in enumerate(page_urls, start=1):

            if index > 1:

                html = self.http.get(page_url)

                if not html:
                    continue

            products = self.parser.parse_products(html)

            if not products:
                self.log.info(
                    "Sem produtos em %s (página %s).",
                    category.name,
                    index,
                )
                break

            for item in products:

                self.repo.save_stub(
                    url=item["url"],
                    name=item["name"],
                    category_id=category.id,
                    category=category_name,
                    subcategory=subcategory_name,
                )

                total_found += 1

        self.log.info(
            "Categoria '%s': %s produtos em %s página(s).",
            category.name,
            total_found,
            len(page_urls),
        )

        return total_found

    # ---------------------------------------------------

    @staticmethod
    def _names(category: Category):

        parts = [p.strip() for p in category.breadcrumb.split(">")]

        parts = [p for p in parts if p]

        category_name = parts[0] if parts else category.name

        subcategory_name = parts[-1] if len(parts) > 1 else ""

        if subcategory_name == category_name:
            subcategory_name = ""

        return category_name, subcategory_name
