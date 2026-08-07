"""Parser da página de produto da Casa Mattos (Fbits, tema "cm-*")."""
from __future__ import annotations

from app.parsers.fbits_product_parser_base import FbitsProductParserBase
from app.selectors import product_selectors_casamattos as sel


class ProductParserCasaMattos(FbitsProductParserBase):
    selectors = sel
