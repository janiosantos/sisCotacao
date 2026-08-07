from __future__ import annotations

import re

from app.config.settings import BASE_URL
from app.selectors.listing_selectors import (
    PAGINATION_LINKS,
    PAGINATION_TOTAL_PAGES,
    PRODUCT_CARD,
    PRODUCT_LINK,
    PRODUCT_NAME,
)
from app.services.html_service import HtmlService
from app.services.url_service import UrlService
from app.utils.format_utils import clean_text
from app.utils.jsonld_utils import jsonld_by_type, jsonld_entries


class ListingParser:

    def parse_products(self, html: str | None) -> list[dict]:

        if not html:
            return []

        soup = HtmlService.soup(html)

        products: dict[str, dict] = {}

        for card in soup.select(PRODUCT_CARD):

            link = card.select_one(PRODUCT_LINK)

            if link is None:
                continue

            href = UrlService.absolute(BASE_URL, link.get("href", ""))

            if not href:
                continue

            name_el = card.select_one(PRODUCT_NAME)

            products[href] = {
                "url": UrlService.normalize(href),
                "name": clean_text(HtmlService.text(name_el)),
            }

        if not products:

            products.update(self._parse_jsonld(soup))

        return list(products.values())

    # ----------------------------------------------------------

    def parse_pagination(
        self,
        html: str | None,
        base_url: str,
    ) -> list[str]:

        if not html:
            return [base_url]

        soup = HtmlService.soup(html)

        total = 1

        info = soup.select_one(PAGINATION_TOTAL_PAGES)

        if info is not None:

            try:
                total = int(clean_text(HtmlService.text(info)))
            except ValueError:
                total = 1

        pages: dict[int, str] = {}

        template: str | None = None

        for link in soup.select(PAGINATION_LINKS):

            href = UrlService.absolute(BASE_URL, link.get("href", ""))

            match = re.search(r"/pagina-(\d+)", href)

            if not match:
                continue

            page = int(match.group(1))

            normalized = UrlService.normalize(href)

            if template is None and page > 1:
                template = re.sub(r"pagina-\d+", "pagina-{n}", normalized)

            if page > 1 and page not in pages:
                pages[page] = normalized

        urls: list[str] = [base_url]

        for page in range(2, total + 1):

            url = pages.get(page)

            if url is None and template is not None:
                url = template.format(n=page)

            if url is None:
                continue

            urls.append(url)

        if not urls:
            urls = [base_url]

        return urls

    # ----------------------------------------------------------

    def _parse_jsonld(self, soup) -> dict[str, dict]:

        products: dict[str, dict] = {}

        entries = jsonld_entries(soup)

        page = jsonld_by_type(entries, "CollectionPage")

        if not page:
            return products

        main_entity = page.get("mainEntity") or {}

        item_list = main_entity.get("itemListElement") or []

        for element in item_list:

            item = element.get("item") or {}

            url = item.get("url") or ""

            if not url:
                continue

            products[UrlService.normalize(url)] = {
                "url": UrlService.normalize(url),
                "name": item.get("name") or "",
            }

        return products
