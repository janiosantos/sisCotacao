from catalog_server.repositories.catalog import CatalogRepository
from catalog_server.repositories.compras import ComprasRepository
from catalog_server.repositories.produtos import ProdutoRepository
from catalog_server.repositories.quotes import QuoteRepository
from catalog_server.repositories.suppliers import SupplierRepository

catalog_repo = CatalogRepository()

produto_repo = ProdutoRepository()

quote_repo = QuoteRepository()

supplier_repo = SupplierRepository()

compras_repo = ComprasRepository()
