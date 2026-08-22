"""Testes de regressão do catálogo (busca, listagem, filtros, detalhe)."""
from __future__ import annotations

import pytest

from catalog_server.db import system_conn
from catalog_server.repositories.catalog import CatalogRepository
from catalog_server.repositories.produtos import ProdutoRepository

from helpers import attrs, criar_familia, variante

repo = ProdutoRepository()
catalog = CatalogRepository()


@pytest.fixture()
def setup(system_db):
    fid = criar_familia(repo)
    aid = {a["nome"]: str(a["id"]) for a in repo.get_familia(fid)["atributos"]}
    pid = repo.create_product(
        familia_id=fid,
        nome="Cabo Flexível Sil",
        marca="Sil",
        descricao="Cabo 750V",
        categoria="Eletrica",
        variantes=[
            variante("ELE-CAB-SIL-25V", "7891001", attrs(aid, Bitola="2,5mm", Cor="Verde"), preco=10.0),
            variante("ELE-CAB-SIL-25A", "7891002", attrs(aid, Bitola="2,5mm", Cor="Azul"), preco=12.0),
        ],
    )
    return {"familia": fid, "attrs": aid, "produto": pid}


def _ids(cards):
    return [c["id"] for c in cards]


def test_list_products_agrupado(setup):
    cards, total = catalog.list_products(agrupado=True, limit=60)
    assert total >= 1
    card = next(c for c in cards if c["id"] == setup["produto"])
    assert card["group"] is True
    assert card["name"] == "Cabo Flexível Sil"
    assert card["variant_count"] == 2
    assert {v["sku"] for v in card["variants"]} == {"ELE-CAB-SIL-25V", "ELE-CAB-SIL-25A"}
    assert card["price_min"] == 10.0
    assert card["price_max"] == 12.0


def test_list_products_flat(setup):
    cards, total = catalog.list_products(agrupado=False, limit=60)
    assert total >= 2
    by_sku = {c["sku"]: c for c in cards}
    assert "ELE-CAB-SIL-25V" in by_sku
    assert by_sku["ELE-CAB-SIL-25V"]["price"] == 10.0


def test_busca_por_sku(setup):
    cards, total = catalog.list_products(agrupado=False, q="ELE-CAB-SIL-25A", limit=60)
    assert total == 1
    assert cards[0]["sku"] == "ELE-CAB-SIL-25A"


def test_busca_por_nome(setup):
    cards, total = catalog.list_products(agrupado=True, q="Cabo Flexível", limit=60)
    assert total == 1
    assert cards[0]["name"] == "Cabo Flexível Sil"


def test_filtro_categoria(setup):
    cards, total = catalog.list_products(categoria="Eletrica", limit=60)
    assert total == 1
    cards2, total2 = catalog.list_products(categoria="Inexistente", limit=60)
    assert total2 == 0


def test_resumo_abc(setup):
    resumo = catalog.resumo_abc()
    assert set(resumo) == {"A", "B", "C", "sem"}
    assert resumo["sem"] >= 1


def test_product_detalhe(setup):
    with system_conn() as conn:
        vid = conn.execute(
            "SELECT id FROM variantes WHERE produto_id=?", (setup["produto"],)
        ).fetchone()[0]
    det = catalog.product(vid)
    assert det is not None
    assert det["sku"] in ("ELE-CAB-SIL-25V", "ELE-CAB-SIL-25A")
    assert det["name"] == "Cabo Flexível Sil"
    assert det["brand"] == "Sil"


def test_products_by_ids(setup):
    with system_conn() as conn:
        rows = conn.execute(
            "SELECT id FROM variantes WHERE produto_id=?", (setup["produto"],)
        ).fetchall()
    ids = [r[0] for r in rows]
    out = catalog.products_by_ids(ids)
    assert len(out) == 2
    for vid, info in out.items():
        assert info["name"] == "Cabo Flexível Sil"
        assert info["sku"] in ("ELE-CAB-SIL-25V", "ELE-CAB-SIL-25A")


def test_categorias(setup):
    tree = catalog.categorias()
    assert "Eletrica" in tree
