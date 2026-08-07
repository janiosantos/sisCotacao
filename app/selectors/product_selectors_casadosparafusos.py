"""
Seletores da página de produto da Casa dos Parafusos (plataforma Fbits).

Separados do site anterior (casadoeletricista) para não interferir nos
seletores existentes. Caso o HTML deste site mude, ajuste APENAS este arquivo.
"""

# Título do produto (painel principal da página).
TITLE = ".pdp-panel--info h1"

# Preço atual (à vista) e preço "de" (tabela/lista).
PRICE_MAIN = ".pdp-panel--info .spot-price-main"
PRICE_LIST = ".pdp-panel--info .product-price-list-price"

# Parcelamento.
INSTALLMENTS = ".pdp-panel--info .spot-price-installments"

# Imagens do produto: miniaturas do desktop (data-src com resolução cheia).
IMAGES = ".pdp-desktop .pdp-thumbs [data-src]"

# Id da variante (asset/sku interno).
VARIANT_ID = "#product-variant-id"

# JSON-LD.
JSONLD_SCRIPT = "script[type='application/ld+json']"
