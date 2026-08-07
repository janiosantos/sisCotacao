from __future__ import annotations

import re
from urllib.parse import urlparse

from app.models.category import Category
from app.selectors.category_selectors import (
    CATEGORY_URL_PATTERN,
    IGNORED_LINK_TEXTS,
    MENU_SELECTORS,
)
from app.services.html_service import HtmlService
from app.services.url_service import UrlService
from app.utils.format_utils import clean_text

from app.config.settings import BASE_URL


class CategoryDiscoveryService:

    def __init__(self):
        self._link_re = re.compile(
            r"^(?P<path>.+?)/c/(?P<cid>\d+)/?$"
        )

    # ----------------------------------------------------------

    def discover(self, html) -> list[Category]:

        soup = HtmlService.soup(html)

        menu = self._find_menu(soup)

        scope = menu if menu is not None else soup

        categories: dict[int, Category] = {}

        for link in scope.find_all("a", href=True):

            href = UrlService.absolute(BASE_URL, link["href"])

            match = self._link_re.match(urlparse(href).path)

            if not match:
                continue

            cid = int(match.group("cid"))

            if cid in categories:
                continue

            name = clean_text(HtmlService.text(link))

            if not name or name.lower() in IGNORED_LINK_TEXTS:
                continue

            segments = match.group("path").strip("/").split("/")

            categories[cid] = Category(
                id=cid,
                parent_id=None,
                level=len(segments) - 1,
                name=name,
                slug=segments[-1],
                breadcrumb=name,
                url=UrlService.normalize(href),
            )

        self._link_parents(categories)

        self._set_breadcrumbs(categories)

        return list(categories.values())

    # ----------------------------------------------------------

    def _find_menu(self, soup):

        for selector in MENU_SELECTORS:

            menu = soup.select_one(selector)

            if menu:
                return menu

        return None

    # ----------------------------------------------------------

    def _link_parents(self, categories: dict[int, Category]):

        by_slug: dict[str, list[Category]] = {}

        for category in categories.values():
            by_slug.setdefault(category.slug, []).append(category)

        for category in categories.values():

            match = self._link_re.match(
                urlparse(category.url).path
            )

            if not match:
                continue

            segments = match.group("path").strip("/").split("/")

            if len(segments) < 2:
                continue

            parent_slug = segments[-2]

            parent_prefix = "/" + "/".join(segments[:-1]) + "/c/"

            for candidate in by_slug.get(parent_slug, []):

                if urlparse(candidate.url).path.startswith(parent_prefix):

                    category.parent_id = candidate.id
                    break

    # ----------------------------------------------------------

    def _set_breadcrumbs(self, categories: dict[int, Category]):

        ordered = sorted(
            categories.values(),
            key=lambda c: (c.level, c.id),
        )

        index = {c.id: c for c in ordered}

        for category in ordered:

            chain: list[str] = []

            current: Category | None = category

            while current is not None:

                chain.append(current.name)

                if current.parent_id is None:
                    break

                current = index.get(current.parent_id)

            category.breadcrumb = " > ".join(reversed(chain))

    # ----------------------------------------------------------

    @staticmethod
    def leaf_categories(categories: list[Category]) -> list[Category]:

        parents = {c.parent_id for c in categories if c.parent_id}

        return [c for c in categories if c.id not in parents]
