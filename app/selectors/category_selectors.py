"""
Seletores centralizados de categorias.

Caso o HTML do site mude, ajuste APENAS os valores deste arquivo.
"""


# Possíveis containers do menu principal.
MENU_SELECTORS = [
    "ul.list-menu-navigation",
    ".list-menu-navigation",
    "#menu",
    ".menu",
    ".main-menu",
    ".header-menu",
    "nav",
]

# A URL de toda categoria segue o padrão .../c/{id}
CATEGORY_URL_PATTERN = r"/c/(\d+)"

# Textos de links que não representam categorias reais.
IGNORED_LINK_TEXTS = {
    "ver todos",
    "ver todas",
    "ver todos produtos",
    "menu",
}
