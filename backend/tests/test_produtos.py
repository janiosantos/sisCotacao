"""Testes de regressão do repositório de produtos (cadastro unificado).

No modelo unificado cada produto é uma unidade independente (as antigas
variações viraram produtos próprios) — não há mais `variantes` nem
`find_or_create_variant`/`_replace_variantes`. O produto carrega seus dados
operacionais (sku, ean, preco, ncm, ...) e atributos (JSONB) diretamente.
"""
from __future__ import annotations

import pytest

from catalog_server.repositories.estoque import estoque_repo
from catalog_server.repositories.produtos import ProdutoRepository

repo = ProdutoRepository()


@pytest.fixture()
def familia(system_db):
    fid = repo.create_familia(
        "Fios e Cabos (teste)",
        "Cabo flexível",
        [
            {"nome": "Bitola", "tipo": "lista", "opcoes": ["2,5mm", "4mm"]},
            {"nome": "Cor", "tipo": "lista", "opcoes": ["Verde", "Azul"]},
        ],
        ncm_padrao="85444900",
        unidade_padrao="MT",
    )
    return fid


@pytest.fixture()
def attr_ids(system_db, familia):
    fam = repo.get_familia(familia)
    return {a["nome"]: a["id"] for a in fam["atributos"]}


def _criar(nome="Cabo Flexível Sil", marca="Sil", categoria="Eletrica",
           descricao="Cabo 750V", familia_id=None, dados=None, atributos=None):
    return repo.create_product(
        familia_id=familia_id,
        nome=nome,
        marca=marca,
        descricao=descricao,
        categoria=categoria,
        dados=dados or {"sku": "SKU", "preco": 10.0},
        atributos=atributos,
    )


def test_criar_produto_unificado(system_db, familia, attr_ids):
    pid = _criar(
        familia_id=familia,
        dados={"sku": "ELE-CAB-SIL-25V", "ean": "7891", "preco": 10.0,
               "ncm": "85444900", "unidade_venda": "MT"},
        atributos={"Bitola": "2,5mm", "Cor": "Verde"},
    )
    prod = repo.get_product(pid)
    assert prod is not None
    assert prod["nome"] == "Cabo Flexível Sil"
    assert prod["categoria"] == "Eletrica"
    assert prod["sku"] == "ELE-CAB-SIL-25V"
    assert prod["ean"] == "7891"
    assert prod["preco"] == 10.0
    assert prod["ncm"] == "85444900"
    assert prod["atributos"]["Bitola"] == "2,5mm"
    assert prod["atributos_nomes"]["Bitola"] == "2,5mm"


def test_update_preserva_sku(system_db, familia, attr_ids):
    pid = _criar(dados={"sku": "SKU-001", "ean": "7890", "preco": 10.0},
                 atributos={"Bitola": "2,5mm"})
    ok, resultado = repo.update_product(
        pid, None, "Cabo Atualizado", "Sil", "", "Eletrica",
        dados={"sku": "SKU-001", "ean": "7890", "preco": 12.0},
        atributos={"Bitola": "2,5mm"},
    )
    assert ok
    prod = repo.get_product(pid)
    assert prod["sku"] == "SKU-001"
    assert prod["ean"] == "7890"
    assert prod["preco"] == 12.0


def test_sku_vazio_e_gerado(system_db):
    pid = _criar(dados={"preco": 5.0})
    prod = repo.get_product(pid)
    assert prod["sku"]  # sku gerado automaticamente


def test_sku_duplicado_ajustado(system_db):
    p1 = _criar(dados={"sku": "SKU-DUP", "preco": 1.0})
    p2 = _criar(nome="Segundo", dados={"sku": "SKU-DUP", "preco": 2.0})
    prod2 = repo.get_product(p2)
    assert prod2["sku"] != "SKU-DUP"
    assert prod2["sku"].startswith("SKU-DUP")


def test_delete_product_desativa(system_db):
    pid = _criar(dados={"sku": "SKU-001", "preco": 10.0})
    estoque_repo.movimentar(1, pid, "entrada", 3)
    ok, resultado = repo.delete_product(pid)
    assert ok
    assert resultado["desativadas"] == 1
    prod = repo.get_product(pid)
    assert prod is not None
    assert prod["ativo"] == 0
