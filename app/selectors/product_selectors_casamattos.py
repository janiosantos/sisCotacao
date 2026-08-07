"""
Seletores da página de produto da Casa Mattos (plataforma Fbits, tema "cm-*").

Tema próprio (Tailwind) — diferente da Casa dos Parafusos. Caso o HTML deste
site mude, ajuste APENAS este arquivo.
"""

# Título do produto (painel principal da página).
TITLE = "main h1"

# Preço atual (à vista) e preço "de" (tabela/lista).
PRICE_MAIN = "#product-prices-div .cm-price-hero"
PRICE_LIST = "#product-prices-div .line-through"

# Parcelamento ("ou R$ ... em até Nx sem juros").
INSTALLMENTS = "#product-prices-div p.mt-1"

# Imagens do produto: miniaturas da galeria (mesmo caminho /img/p/ em resolução cheia).
IMAGES = ".cm-pdp-thumbs img"

# Id da variante (asset/sku interno).
VARIANT_ID = "#product-variant-id"

# JSON-LD.
JSONLD_SCRIPT = "script[type='application/ld+json']"
