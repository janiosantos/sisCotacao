"""
Seletores centralizados das páginas de listagem (categoria/produtos).

Caso o HTML do site mude, ajuste APENAS os valores deste arquivo.
"""

import re

# Cartão individual de produto na grade de listagem.
PRODUCT_CARD = "li.item-produto"

# Link para a página de detalhes do produto.
PRODUCT_LINK = 'a[href*="/p/"]'

# Nome do produto dentro do cartão.
PRODUCT_NAME = "span.product-name"

# Container da listagem de produtos.
LISTING_CONTAINER = "ul.listagem-produtos"

# Padrão de URL de produto: .../p/{id}
PRODUCT_URL_PATTERN = re.compile(r"/p/(\d+)")

# Total de páginas exibido no topo da listagem.
PAGINATION_TOTAL_PAGES = ".quantidade-paginas-paginacao-topo"

# Links de paginação (podem existir quando a categoria tem várias páginas).
PAGINATION_LINKS = 'a[href*="/pagina-"]'

# Link "próxima página" (fallback).
NEXT_LINK = "a.next"
