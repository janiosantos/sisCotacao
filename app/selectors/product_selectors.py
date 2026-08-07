"""
Seletores centralizados da página de detalhes do produto.

Caso o HTML do site mude, ajuste APENAS os valores deste arquivo.
"""

# Título do produto.
TITLE = "#titulo-produto h1.titulo"
TITLE_MOBILE = "#titulo-produto-mobile .titulo"

# Código interno do produto.
COD_PRODUCT = ".cod-produto"

# Preços.
PRICE_ATUAL = "#preco-produto .preco-atual"
PRICE_DE = "#preco-produto .preco-de"

# Preço à vista (boleto/pix).
PIX_PRICE = ".condicoes-pagamento-com-desconto li.boleto .price-description b"
PIX_LABEL = ".condicoes-pagamento-com-desconto li.boleto .label"

# Parcelamento.
INSTALLMENTS = ".preco-emvezes .descricao"

# Marca (logotipo com atributo alt).
BRAND_IMG = ".marca-produto a img"

# Cor / atributos do produto.
COLOR = 'li.selecione-tamanho[data-attribute-type="c"] .nome-cor'

# Descrição curta (quando existir).
SHORT_DESCRIPTION = ".content-labels-below-summarized-description"

# Descrição longa.
LONG_DESCRIPTION = "#descricao-produto .texto-descricao"

# Imagens do produto (resolução original no atributo data-original).
IMAGES = "#fotos-produto .viewer-images-container img"

# Breadcrumb (trilha de navegação).
BREADCRUMB = "ul.breadcrumb li a"

# JSON-LD.
JSONLD_SCRIPT = "script[type='application/ld+json']"
