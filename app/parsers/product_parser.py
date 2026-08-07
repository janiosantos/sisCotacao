from __future__ import annotations

from app.selectors.product_selectors import (
    BRAND_IMG,
    COD_PRODUCT,
    COLOR,
    INSTALLMENTS,
    LONG_DESCRIPTION,
    PIX_PRICE,
    PRICE_ATUAL,
    PRICE_DE,
    SHORT_DESCRIPTION,
    TITLE,
    TITLE_MOBILE,
    IMAGES,
)
from app.services.html_service import HtmlService
from app.utils.format_utils import clean_text, parse_price_brl
from app.utils.jsonld_utils import jsonld_by_type, jsonld_entries


class ProductParser:

    def parse(self, html: str | None, url: str = "") -> dict:

        if not html:
            return {}

        soup = HtmlService.soup(html)

        entries = jsonld_entries(soup)

        product_ld = jsonld_by_type(entries, "Product") or {}

        data = {
            "url": url or self._canonical(soup) or product_ld.get("url") or "",
            "name": self._name(soup, product_ld),
            "sku": self._sku(soup, product_ld),
            "ean": str(product_ld.get("gtin13") or ""),
            "brand": self._brand(soup, product_ld),
            "color": self._color(soup, product_ld),
            "price": parse_price_brl(HtmlService.text(soup.select_one(PRICE_ATUAL))),
            "old_price": parse_price_brl(HtmlService.text(soup.select_one(PRICE_DE))),
            "pix_price": parse_price_brl(HtmlService.text(soup.select_one(PIX_PRICE))),
            "installment": clean_text(HtmlService.text(soup.select_one(INSTALLMENTS))),
            "short_description": self._short_description(soup, product_ld),
            "long_description": self._long_description(soup, product_ld),
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

        element = soup.select_one(TITLE) or soup.select_one(TITLE_MOBILE)

        name = clean_text(HtmlService.text(element))

        return name or product_ld.get("name") or ""

    # ----------------------------------------------------------

    @staticmethod
    def _sku(soup, product_ld):

        sku = str(product_ld.get("sku") or "").strip()

        if sku:
            return sku

        cod = soup.select_one(COD_PRODUCT)

        text = clean_text(HtmlService.text(cod))

        if text and ":" in text:
            return text.split(":", 1)[1].strip()

        return text

    # ----------------------------------------------------------

    @staticmethod
    def _brand(soup, product_ld):

        img = soup.select_one(BRAND_IMG)

        if img is not None:
            brand = img.get("alt", "").strip()
            if brand:
                return brand

        manufacturer = product_ld.get("manufacturer") or {}

        return manufacturer.get("name") or ""

    # ----------------------------------------------------------

    @staticmethod
    def _color(soup, product_ld):

        element = soup.select_one(COLOR)

        color = clean_text(HtmlService.text(element))

        if color:
            return color.title()

        return str(product_ld.get("color") or "").title()

    # ----------------------------------------------------------

    @staticmethod
    def _short_description(soup, product_ld):

        element = soup.select_one(SHORT_DESCRIPTION)

        text = clean_text(HtmlService.text(element))

        if text:
            return text[:500]

        meta = soup.select_one("meta[name='description']")

        if meta is not None:
            text = clean_text(meta.get("content", ""))

        if not text:

            description = product_ld.get("description") or ""

            text = clean_text(description.split("\n\n")[0])[:500]

        return text[:500]

    # ----------------------------------------------------------

    @staticmethod
    def _long_description(soup, product_ld):

        element = soup.select_one(LONG_DESCRIPTION)

        text = clean_text(element.get_text("\n")) if element else ""

        if text:
            return text

        description = product_ld.get("description") or ""

        return clean_text(description)

    # ----------------------------------------------------------

    @staticmethod
    def _images(soup, product_ld):

        images = []

        for img in soup.select(IMAGES):

            src = img.get("data-original") or img.get("src") or ""

            if src and src not in images:
                images.append(src)

        if not images:

            og = soup.select_one("meta[property='og:image']")

            if og is not None and og.get("content"):
                images.append(og["content"])

        if not images:

            ld_images = product_ld.get("image") or []

            if isinstance(ld_images, str):
                ld_images = [ld_images]

            images = [img for img in ld_images if img]

        return images
