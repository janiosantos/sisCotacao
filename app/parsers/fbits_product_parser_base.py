"""Parser base para páginas de produto de lojas Fbits.

O JSON-LD `Product` é idêntico entre as lojas Fbits (nome, sku, gtin/gtin13,
brand.name, offers.price, image[]). O que muda entre os temas é o HTML, então
cada loja fornece o próprio módulo de seletores. Este base concentra a lógica
comum para as lojas novas; a Casa dos Parafusos mantém o parser próprio.
"""
from __future__ import annotations

import re

from app.services.html_service import HtmlService
from app.utils.format_utils import clean_text, parse_price_brl
from app.utils.jsonld_utils import jsonld_by_type, jsonld_entries


class FbitsProductParserBase:
    """Devolve o mesmo shape do `ProductParser` (casadoeletricista)."""

    # Módulo com TITLE, PRICE_MAIN, PRICE_LIST, INSTALLMENTS, IMAGES, VARIANT_ID.
    selectors = None

    def parse(self, html: str | None, url: str = "") -> dict:

        if not html:
            return {}

        sel = self.selectors
        soup = HtmlService.soup(html)

        product_ld = jsonld_by_type(jsonld_entries(soup), "Product") or {}

        price = self._price(soup, product_ld)

        data = {
            "url": url or self._canonical(soup) or product_ld.get("url") or "",
            "name": self._name(soup, product_ld),
            "sku": self._sku(soup, product_ld),
            "ean": self._ean(product_ld),
            "brand": self._brand(product_ld),
            "color": "",
            "price": price,
            "old_price": self._old_price(soup),
            "pix_price": price,
            "installment": (
                clean_text(HtmlService.text(soup.select_one(sel.INSTALLMENTS)))
                if sel.INSTALLMENTS else ""
            ),
            "short_description": self._description(product_ld),
            "long_description": self._description(product_ld),
            "images": self._images(soup, product_ld),
        }

        return data

    # ----------------------------------------------------------

    @staticmethod
    def _canonical(soup):

        link = soup.select_one("link[rel='canonical']")

        return link.get("href", "") if link else ""

    # ----------------------------------------------------------

    @classmethod
    def _name(cls, soup, product_ld):

        element = soup.select_one(cls.selectors.TITLE) if cls.selectors.TITLE else None

        name = clean_text(HtmlService.text(element))

        return name or product_ld.get("name") or ""

    # ----------------------------------------------------------

    @classmethod
    def _sku(cls, soup, product_ld):

        sku = str(product_ld.get("sku") or "").strip()

        if sku:
            return sku

        vid = soup.select_one(cls.selectors.VARIANT_ID)

        return (vid.get("value", "") or "").strip() if vid is not None else ""

    # ----------------------------------------------------------

    @staticmethod
    def _ean(product_ld):

        raw = product_ld.get("gtin13") or product_ld.get("gtin") or ""

        return str(raw)

    # ----------------------------------------------------------

    @staticmethod
    def _brand(product_ld):

        brand = product_ld.get("brand") or {}

        return brand.get("name") or ""

    # ----------------------------------------------------------

    @classmethod
    def _price(cls, soup, product_ld):

        value = parse_price_brl(HtmlService.text(soup.select_one(cls.selectors.PRICE_MAIN)))

        if value is not None:
            return value

        offers = product_ld.get("offers") or {}

        try:
            return float(offers.get("price"))
        except (TypeError, ValueError):
            return None

    # ----------------------------------------------------------

    @classmethod
    def _old_price(cls, soup):

        if not cls.selectors.PRICE_LIST:
            return None

        return parse_price_brl(HtmlService.text(soup.select_one(cls.selectors.PRICE_LIST)))

    # ----------------------------------------------------------

    @staticmethod
    def _description(product_ld):

        return clean_text(product_ld.get("description") or "")

    # ----------------------------------------------------------

    @classmethod
    def _images(cls, soup, product_ld):

        images = []

        if cls.selectors.IMAGES:
            for img in soup.select(cls.selectors.IMAGES):

                src = img.get("data-src") or img.get("src") or ""

                src = re.sub(r"\?.*", "", src)

                if src and src not in images:
                    images.append(src)

        if not images:

            ld_images = product_ld.get("image") or []

            if isinstance(ld_images, str):
                ld_images = [ld_images]

            images = [re.sub(r"\?.*", "", img) for img in ld_images if img]

        return images
