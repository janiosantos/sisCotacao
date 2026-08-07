from __future__ import annotations

import re

from app.selectors.product_selectors_casadosparafusos import (
    IMAGES,
    INSTALLMENTS,
    PRICE_LIST,
    PRICE_MAIN,
    TITLE,
    VARIANT_ID,
)
from app.services.html_service import HtmlService
from app.utils.format_utils import clean_text, parse_price_brl
from app.utils.jsonld_utils import jsonld_by_type, jsonld_entries


class ProductParserCasadosParafusos:
    """Parser da página de produto da Casa dos Parafusos (Fbits).

    Devolve o mesmo shape do `ProductParser` (casadoeletricista): url, name,
    sku, ean, brand, color, price, old_price, pix_price, installment,
    short_description, long_description, images.
    """

    def parse(self, html: str | None, url: str = "") -> dict:

        if not html:
            return {}

        soup = HtmlService.soup(html)

        product_ld = jsonld_by_type(jsonld_entries(soup), "Product") or {}

        data = {
            "url": url or self._canonical(soup) or product_ld.get("url") or "",
            "name": self._name(soup, product_ld),
            "sku": self._sku(soup, product_ld),
            "ean": str(product_ld.get("gtin13") or ""),
            "brand": self._brand(product_ld),
            "color": "",
            "price": self._price(soup, product_ld),
            "old_price": self._old_price(soup),
            "pix_price": self._price(soup, product_ld),
            "installment": clean_text(HtmlService.text(soup.select_one(INSTALLMENTS))),
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

    @staticmethod
    def _name(soup, product_ld):

        element = soup.select_one(TITLE)

        name = clean_text(HtmlService.text(element))

        return name or product_ld.get("name") or ""

    # ----------------------------------------------------------

    @staticmethod
    def _sku(soup, product_ld):

        sku = str(product_ld.get("sku") or "").strip()

        if sku:
            return sku

        vid = soup.select_one(VARIANT_ID)

        return (vid.get("value", "") or "").strip() if vid is not None else ""

    # ----------------------------------------------------------

    @staticmethod
    def _brand(product_ld):

        brand = product_ld.get("brand") or {}

        return brand.get("name") or ""

    # ----------------------------------------------------------

    @staticmethod
    def _price(soup, product_ld):

        value = parse_price_brl(HtmlService.text(soup.select_one(PRICE_MAIN)))

        if value is not None:
            return value

        offers = product_ld.get("offers") or {}

        raw = offers.get("price")

        try:
            return float(raw)
        except (TypeError, ValueError):
            return None

    # ----------------------------------------------------------

    @staticmethod
    def _old_price(soup):

        return parse_price_brl(HtmlService.text(soup.select_one(PRICE_LIST)))

    # ----------------------------------------------------------

    @staticmethod
    def _description(product_ld):

        description = product_ld.get("description") or ""

        return clean_text(description)

    # ----------------------------------------------------------

    @staticmethod
    def _images(soup, product_ld):

        images = []

        for img in soup.select(IMAGES):

            src = img.get("data-src") or ""

            src = re.sub(r"\?.*", "", src)

            if src and src not in images:
                images.append(src)

        if not images:

            ld_images = product_ld.get("image") or []

            if isinstance(ld_images, str):
                ld_images = [ld_images]

            images = [re.sub(r"\?.*", "", img) for img in ld_images if img]

        return images
