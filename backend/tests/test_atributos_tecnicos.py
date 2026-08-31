"""Atributos técnicos do ramo em colunas relacionais (MDM-004)."""
from __future__ import annotations

from catalog_server.db import system_conn
from catalog_server.repositories import produto_repo


def _criar_produto(dados: dict | None = None) -> int:
    dados = dados or {}
    return produto_repo.create_product(
        familia_id=None,
        nome="Cabo 2,5mm",
        marca="MarcaX",
        descricao="Cabo de cobre",
        categoria="",
        subcategoria="",
        dados=dados,
        atributos={},
    )


def test_create_persiste_tecnicos(system_db):
    pid = _criar_produto({
        "sku": "CAB-25",
        "preco": 3.2,
        "bitola": "2,5mm²",
        "tensao": "220V",
        "material": "Cobre",
        "cor": "Azul",
        "validade_dias": 365,
    })
    p = produto_repo.get_product(pid)
    assert p["bitola"] == "2,5mm²"
    assert p["tensao"] == "220V"
    assert p["material"] == "Cobre"
    assert p["cor"] == "Azul"
    assert int(p["validade_dias"]) == 365


def test_update_atualiza_tecnicos(system_db):
    pid = _criar_produto({"sku": "TUB-32", "preco": 8.0, "diametro": "1/2"})
    ok, _ = produto_repo.update_product(
        pid,
        familia_id=None,
        nome="Tubo 32",
        marca="MarcaX",
        descricao="Tubo",
        categoria="",
        subcategoria="",
        dados={"sku": "TUB-32", "preco": 8.0, "diametro": "3/4", "rosca": "M8"},
    )
    assert ok
    p = produto_repo.get_product(pid)
    assert p["diametro"] == "3/4"
    assert p["rosca"] == "M8"


def test_tecnicos_padrao_vazio(system_db):
    pid = _criar_produto({"sku": "SIM-1", "preco": 1.0})
    p = produto_repo.get_product(pid)
    assert (p["bitola"] or "") == ""
    assert p["tensao"] is None or p["tensao"] == ""
    assert int(p["validade_dias"]) == 0 if p["validade_dias"] else True


def test_colunas_existem(system_db):
    with system_conn() as conn:
        cols = {r["column_name"] for r in conn.execute(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name='produtos_cadastro'"
        ).fetchall()}
    for col in ("bitola", "tensao", "potencia", "comprimento", "diametro",
                "rosca", "material", "cor", "norma", "validade_dias", "garantia_dias"):
        assert col in cols, f"coluna {col} ausente"


def test_indices_existem(system_db):
    with system_conn() as conn:
        idxs = {r["indexname"] for r in conn.execute(
            "SELECT indexname FROM pg_indexes WHERE tablename='produtos_cadastro'"
        ).fetchall()}
    for nome in ("idx_produtos_bitola", "idx_produtos_cor", "idx_produtos_material", "idx_produtos_rosca"):
        assert nome in idxs, f"índice {nome} ausente"