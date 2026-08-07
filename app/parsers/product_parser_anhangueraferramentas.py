"""Parser da página de produto da Anhanguera Ferramentas (Fbits)."""
from __future__ import annotations

from app.parsers.fbits_product_parser_base import FbitsProductParserBase
from app.selectors import product_selectors_anhangueraferramentas as sel


class ProductParserAnhangueraFerramentas(FbitsProductParserBase):
    selectors = sel
