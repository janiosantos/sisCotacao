"""Testes de regressão do catálogo (busca, listagem, filtros, detalhe)."""
from __future__ import annotations

import pytest

from catalog_server.repositories.catalog import CatalogRepository
from catalog_server.repositories.produtos import ProdutoRepository

from helpers import criar_familia, produto_dados

repo = ProdutoRepository()
catalog = CatalogRepository()


@pytest.fixture()
def setup(system_db):
    fid = criar_familia(repo)
    pid1 = repo.create_product(
        familia_id=fid,
        nome="Cabo Flexível Sil",
        marca="Sil",
        descricao="Cabo 750V",
        categoria="Eletrica",
        dados=produto_dados("ELE-CAB-SIL-25V", "7891001", preco=10.0),
        atributos={"Bitola": "2,5mm", "Cor": "Verde"},
    )
    pid2 = repo.create_product(
        familia_id=fid,
        nome="Cabo Flexível Sil",
        marca="Sil",
        descricao="Cabo 750V",
        categoria="Eletrica",
        dados=produto_dados("ELE-CAB-SIL-25A", "7891002", preco=12.0),
        atributos={"Bitola": "2,5mm", "Cor": "Azul"},
    )
    return {"familia": fid, "produto": pid1, "produto2": pid2}


def _ids(cards):
    return [c["id"] for c in cards]


def test_list_products_agrupado(setup):
    cards, total = catalog.list_products(agrupado=True, limit=60)
    assert total == 2
    card = next(c for c in cards if c["id"] == setup["produto"])
    assert card["group"] is False
    assert card["name"] == "Cabo Flexível Sil"
    assert card["sku"] == "ELE-CAB-SIL-25V"
    assert card["price"] == 10.0


def test_list_products_flat(setup):
    cards, total = catalog.list_products(agrupado=False, limit=60)
    assert total == 2
    by_sku = {c["sku"]: c for c in cards}
    assert "ELE-CAB-SIL-25V" in by_sku
    assert by_sku["ELE-CAB-SIL-25V"]["price"] == 10.0


def test_busca_por_sku(setup):
    cards, total = catalog.list_products(agrupado=False, q="ELE-CAB-SIL-25A", limit=60)
    assert total == 1
    assert cards[0]["sku"] == "ELE-CAB-SIL-25A"


def test_busca_por_nome(setup):
    cards, total = catalog.list_products(agrupado=True, q="Cabo Flexível", limit=60)
    assert total >= 1
    assert cards[0]["name"] == "Cabo Flexível Sil"


def test_filtro_categoria(setup):
    cards, total = catalog.list_products(categoria="Eletrica", limit=60)
    assert total == 2
    cards2, total2 = catalog.list_products(categoria="Inexistente", limit=60)
    assert total2 == 0


def test_resumo_abc(setup):
    resumo = catalog.resumo_abc()
    assert set(resumo) == {"A", "B", "C", "sem"}
    assert resumo["sem"] >= 1


def test_product_detalhe(setup):
    det = catalog.product(setup["produto"])
    assert det is not None
    assert det["sku"] == "ELE-CAB-SIL-25V"
    assert det["name"] == "Cabo Flexível Sil"
    assert det["brand"] == "Sil"


def test_products_by_ids(setup):
    ids = [setup["produto"], setup["produto2"]]
    out = catalog.products_by_ids(ids)
    assert len(out) == 2
    for vid, info in out.items():
        assert info["name"] == "Cabo Flexível Sil"
        assert info["sku"] in ("ELE-CAB-SIL-25V", "ELE-CAB-SIL-25A")


def test_categorias(setup):
    tree = catalog.categorias()
    assert "Eletrica" in tree
