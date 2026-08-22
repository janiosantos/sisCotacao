from catalog_server.repositories.catalog import CatalogRepository
from catalog_server.repositories.clientes import cliente_repo
from catalog_server.repositories.compras import ComprasRepository
from catalog_server.repositories.orcamentos import OrcamentoRepository
from catalog_server.repositories.plano_contas import plano_conta_repo
from catalog_server.repositories.produtos import ProdutoRepository
from catalog_server.repositories.quotes import QuoteRepository
from catalog_server.repositories.suppliers import SupplierRepository
from catalog_server.repositories.usuarios import usuario_repo
from catalog_server.repositories.vendedores import vendedor_repo

catalog_repo = CatalogRepository()

orcamento_repo = OrcamentoRepository()

produto_repo = ProdutoRepository()

quote_repo = QuoteRepository()

supplier_repo = SupplierRepository()

from catalog_server.repositories.bancos import banco_repo
from catalog_server.repositories.compras_avancado import fornecedor_preco_repo, fornecedor_preferencial_repo, ibpt_repo, solicitacao_repo, tolerancia_repo
from catalog_server.repositories.depositos import deposito_repo, expedicao_repo
from catalog_server.repositories.diagnostico import diagnostico_repo
from catalog_server.repositories.estoque import estoque_repo, lote_repo
from catalog_server.repositories.financeiro import adiantamento_repo, caixa_repo, centro_custo_repo, condicao_repo, contas_repo
from catalog_server.repositories.pdv_frete import desconto_repo, frete_repo
from catalog_server.repositories.fiscal import (
    beneficio_fiscal_repo,
    cest_repo,
    cfop_repo,
    csosn_repo,
    cst_repo,
    fiscal_config_repo,
)
from catalog_server.repositories.fiscal_avancado import emitente_repo, nfe_entrada_repo, nfe_saida_repo
from catalog_server.repositories.fiscal_regras import fiscal_regra_repo, fiscal_regra_versao_repo
from catalog_server.repositories import dashboard
from catalog_server.repositories import loja
from catalog_server.repositories.posvenda import garantia_repo, interacao_repo
from catalog_server.repositories.precos import (
    preco_historico_repo,
    promocao_repo,
    revisao_repo,
    tabela_preco_repo,
)

compras_repo = ComprasRepository()
