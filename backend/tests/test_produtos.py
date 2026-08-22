"""Testes de regressão do repositório de produtos (cadastro, variações)."""
from __future__ import annotations

import pytest

from catalog_server.db import system_conn
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
    return {a["nome"]: str(a["id"]) for a in fam["atributos"]}


def _attrs(attr_ids: dict, **vals: str) -> dict:
    return {attr_ids[k]: v for k, v in vals.items()}


def _variante(sku: str, ean: str, attrs: dict, preco: float = 10.0) -> dict:
    return {
        "sku": sku,
        "ean": ean,
        "preco": preco,
        "preco_promocional": None,
        "observacao": "",
        "atributos": attrs,
        "ncm": "",
        "unidade_venda": "MT",
    }


def _id_por_sku(prod, sku: str) -> int:
    return next(v["id"] for v in prod["variantes"] if v["sku"] == sku)


def test_criar_produto_com_variantes(system_db, familia, attr_ids):
    pid = repo.create_product(
        familia_id=familia,
        nome="Cabo Flexível Sil",
        marca="Sil",
        descricao="Cabo 750V",
        categoria="Eletrica",
        variantes=[
            _variante("ELE-CAB-SIL-25V", "7891", _attrs(attr_ids, Bitola="2,5mm", Cor="Verde")),
            _variante("ELE-CAB-SIL-25A", "7892", _attrs(attr_ids, Bitola="2,5mm", Cor="Azul")),
        ],
    )
    prod = repo.get_product(pid)
    assert prod is not None
    assert prod["nome"] == "Cabo Flexível Sil"
    assert prod["categoria"] == "Eletrica"
    assert len(prod["variantes"]) == 2
    by_sku = {v["sku"]: v for v in prod["variantes"]}
    assert by_sku["ELE-CAB-SIL-25V"]["preco"] == 10.0
    assert by_sku["ELE-CAB-SIL-25V"]["atributos_nomes"]["Bitola"] == "2,5mm"
    # NCM herdado da família na variante
    assert by_sku["ELE-CAB-SIL-25V"]["ncm"] == "85444900"
    # fiscal_config 1:1 criado pelo _sync_ncm
    vid = _id_por_sku(prod, "ELE-CAB-SIL-25V")
    with system_conn() as conn:
        n = conn.execute(
            "SELECT COUNT(*) FROM fiscal_config WHERE variante_id=?", (vid,)
        ).fetchone()[0]
    assert n == 1


def test_update_preserva_sku_ean(system_db, familia, attr_ids):
    pid = repo.create_product(
        familia_id=familia,
        nome="Cabo",
        marca="Sil",
        descricao="",
        categoria="Eletrica",
        variantes=[_variante("SKU-001", "7890", _attrs(attr_ids, Bitola="2,5mm"))],
    )
    vid = _id_por_sku(repo.get_product(pid), "SKU-001")
    # Update enviando a mesma variante com id preserva sku/ean
    ok, _ = repo.update_product(
        pid, familia, "Cabo Atualizado", "Sil", "", "Eletrica",
        [{"id": vid, "sku": "SKU-001", "ean": "7890", "preco": 12.0,
          "preco_promocional": None, "observacao": "",
          "atributos": _attrs(attr_ids, Bitola="2,5mm"), "unidade_venda": "MT"}],
    )
    assert ok
    prod = repo.get_product(pid)
    v = prod["variantes"][0]
    assert v["sku"] == "SKU-001"
    assert v["ean"] == "7890"
    assert v["preco"] == 12.0


def test_regra_remover_variante_exclui_sem_dependencia(system_db, familia, attr_ids):
    pid = repo.create_product(
        familia_id=familia,
        nome="Cabo",
        marca="Sil",
        descricao="",
        categoria="Eletrica",
        variantes=[_variante("SKU-EXC", "7890", _attrs(attr_ids, Bitola="2,5mm"), preco=0)],
    )
    # Remove o fiscal_config criado pelo _sync_ncm para isolar a regra:
    # sem dependências (incluindo fiscal), a variante deve ser excluída.
    vid = _id_por_sku(repo.get_product(pid), "SKU-EXC")
    with system_conn() as conn:
        conn.execute("DELETE FROM fiscal_config WHERE variante_id=?", (vid,))
        conn.execute("DELETE FROM variante_atributos WHERE variante_id=?", (vid,))
        conn.execute("UPDATE variantes SET ncm='' WHERE id=?", (vid,))
        destino = repo._regra_remover_variante(conn, vid)
    assert destino == "excluidas"


def test_regra_remover_variante_desativa_com_estoque(system_db, familia, attr_ids):
    pid = repo.create_product(
        familia_id=familia,
        nome="Cabo",
        marca="Sil",
        descricao="",
        categoria="Eletrica",
        variantes=[_variante("SKU-DEP", "7890", _attrs(attr_ids, Bitola="2,5mm"))],
    )
    vid = _id_por_sku(repo.get_product(pid), "SKU-DEP")
    estoque_repo.movimentar(1, vid, "entrada", 5, documento="TST")
    with system_conn() as conn:
        destino = repo._regra_remover_variante(conn, vid)
    assert destino == "desativadas"
    with system_conn() as conn:
        ativo = conn.execute(
            "SELECT ativo FROM variantes WHERE id=?", (vid,)
        ).fetchone()[0]
    assert ativo == 0


def test_find_or_create_variant_reusa_existente(system_db, familia, attr_ids):
    pid = repo.create_product(
        familia_id=familia,
        nome="Cabo",
        marca="Sil",
        descricao="",
        categoria="Eletrica",
        variantes=[_variante("SKU-001", "7890", _attrs(attr_ids, Bitola="2,5mm", Cor="Verde"))],
    )
    # usa os ids reais dos atributos da família
    a_b = int(attr_ids["Bitola"])
    a_c = int(attr_ids["Cor"])
    vid2 = repo.find_or_create_variant(pid, {a_b: "2,5mm", a_c: "Verde"}, "Sil")
    assert vid2 == _id_por_sku(repo.get_product(pid), "SKU-001")
    vid3 = repo.find_or_create_variant(pid, {a_b: "2,5mm", a_c: "Azul"}, "Sil")
    assert vid3 != vid2


def test_delete_product_desativa_com_dependencias(system_db, familia, attr_ids):
    pid = repo.create_product(
        familia_id=familia,
        nome="Cabo",
        marca="Sil",
        descricao="",
        categoria="Eletrica",
        variantes=[_variante("SKU-001", "7890", _attrs(attr_ids, Bitola="2,5mm"))],
    )
    vid = _id_por_sku(repo.get_product(pid), "SKU-001")
    estoque_repo.movimentar(1, vid, "entrada", 3)
    ok, resultado = repo.delete_product(pid)
    assert ok
    assert resultado["desativadas"] == 1
    assert repo.get_product(pid) is not None  # desativado, não removido