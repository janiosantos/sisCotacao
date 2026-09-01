"""Testes de regressão de precificação (tabelas, itens, geração de preços, promoções)."""
from __future__ import annotations

import pytest

from catalog_server.db import system_conn
from catalog_server.repositories.precos import (
    promocao_repo,
    revisao_repo,
    tabela_preco_repo,
)
from catalog_server.repositories.produtos import ProdutoRepository

from helpers import criar_familia, produto_dados

repo = ProdutoRepository()


@pytest.fixture()
def tabela(system_db):
    return tabela_preco_repo.create("Varejo", tipo="varejo", margem=20, markup=0)


@pytest.fixture()
def produto_id(system_db):
    fid = criar_familia(repo)
    pid = repo.create_product(
        familia_id=fid,
        nome="Cabo Flexível Sil",
        marca="Sil",
        descricao="",
        categoria="Eletrica",
        dados=produto_dados("SKU-PRECO", "7893001", preco=10.0),
        atributos={"Bitola": "2,5mm"},
    )
    with system_conn() as conn:
        # custo para a geração de preço
        conn.execute("UPDATE produtos_cadastro SET custo_unitario=8.0 WHERE id=?", (pid,))
    return pid


def test_tabela_crud(tabela):
    tab = tabela_preco_repo.get(tabela)
    assert tab["nome"] == "Varejo"
    assert tab["tipo"] == "varejo"
    assert tabela_preco_repo.update(tabela, "Atacado", "atacado", 25, 0)
    assert tabela_preco_repo.set_ativo(tabela, False)
    ativos = tabela_preco_repo.list(somente_ativos=True)
    assert tabela not in [t["id"] for t in ativos]


def test_upsert_item(tabela, produto_id):
    assert tabela_preco_repo.upsert_item(tabela, produto_id, 12.5, margem=20)
    itens = tabela_preco_repo.list_itens(tabela)
    assert len(itens) == 1
    assert itens[0]["preco"] == 12.5
    assert itens[0]["sku"] == "SKU-PRECO"
    # upsert de novo preço
    assert tabela_preco_repo.upsert_item(tabela, produto_id, 13.0)
    itens = tabela_preco_repo.list_itens(tabela)
    assert len(itens) == 1
    assert itens[0]["preco"] == 13.0


def test_gerar_precos_markup(tabela, produto_id):
    assert tabela_preco_repo.gerar_precos(tabela, markup=25) == 1
    itens = tabela_preco_repo.list_itens(tabela)
    # custo 8.0 * 1.25 = 10.0
    assert itens[0]["preco"] == 10.0


def test_gerar_precos_margem(tabela, produto_id):
    assert tabela_preco_repo.gerar_precos(tabela, margem=20) == 1
    itens = tabela_preco_repo.list_itens(tabela)
    # 8.0 / (1 - 0.20) = 10.0
    assert itens[0]["preco"] == 10.0
    assert itens[0]["margem"] == 20.0


def test_delete_item(tabela, produto_id):
    tabela_preco_repo.upsert_item(tabela, produto_id, 12.5)
    assert tabela_preco_repo.delete_item(tabela, produto_id)
    assert tabela_preco_repo.list_itens(tabela) == []


def test_promocao_percentual(produto_id):
    pid = promocao_repo.create("Liquida", "percentual", 10)
    assert promocao_repo.aplicar_promocao(pid, [produto_id], "percentual", 10) == 1
    itens = promocao_repo.list_itens(pid)
    assert len(itens) == 1
    assert itens[0]["preco_promocional"] == 9.0  # 10.0 - 10%


def test_promocao_valor_fixo(produto_id):
    pid = promocao_repo.create("Liquida", "valor_fixo", 8.5)
    assert promocao_repo.aplicar_promocao(pid, [produto_id], "valor_fixo", 8.5) == 1
    itens = promocao_repo.list_itens(pid)
    assert itens[0]["preco_promocional"] == 8.5


def test_revisao_abre_fecha(tabela):
    rid = revisao_repo.create(tabela, "REV-001", "Revisão inicial")
    assert revisao_repo.get(rid)["situacao"] == "aberta"
    assert revisao_repo.fechar(rid)
    assert revisao_repo.get(rid)["situacao"] == "fechada"
    # fechar de novo não deve fazer nada
    assert not revisao_repo.fechar(rid)
