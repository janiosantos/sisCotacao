"""
Seletores da página de produto da Anhanguera Ferramentas (plataforma Fbits).

Tema próprio ("product-*") — diferente da Casa dos Parafusos e da Casa Mattos.
Caso o HTML deste site mude, ajuste APENAS este arquivo.
"""

# Título do produto.
TITLE = "h1.product-title"

# Preço atual (à vista no PIX) — dentro do bloco #product-prices-div do produto.
# NB: escopo pelo id do produto; o seletor genérico ".spot-price ..." casava o 1º
# bloco da página, que pode ser de um produto "relacionado" (preço errado).
PRICE_MAIN = "#product-prices-div .product-price_value"

# Preço "de" (tabela/lista) do próprio produto.
PRICE_LIST = "#product-prices-div .product-price_older"

# Parcelamento.
INSTALLMENTS = "#product-prices-div .product-installment"

# Imagens do produto: slider principal (cai para o JSON-LD se vazio).
IMAGES = ".product-image_main-slider img"

# Id da variante (asset/sku interno).
VARIANT_ID = "#product-variant-id"

# JSON-LD.
JSONLD_SCRIPT = "script[type='application/ld+json']"
