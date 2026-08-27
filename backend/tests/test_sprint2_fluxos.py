"""Testes do Sprint 2+3: atributos JSONB, SKU nos fluxos manuais e marcas.

No modelo unificado cada produto é uma unidade independente: os atributos vivem
no JSONB `produtos_cadastro.atributos` (não há mais `variantes`/EAV nem
`find_or_create_variant`). Marcas fazem create-or-get e vinculam
`produtos_cadastro.marca_id`.
"""
from __future__ import annotations

import pytest

from catalog_server.db import system_conn
from catalog_server.repositories import marcas as marcas_repo
from catalog_server.repositories.produtos import ProdutoRepository

repo = ProdutoRepository()


@pytest.fixture()
def familia(system_db):
    return repo.create_familia(
        "Fios e Cabos (sprint2)",
        "Cabo flexível",
        [
            {"nome": "Bitola", "tipo": "lista", "opcoes": ["2,5mm", "4mm"]},
            {"nome": "Cor", "tipo": "lista", "opcoes": ["Verde", "Azul"]},
        ],
    )


@pytest.fixture()
def attr_ids(system_db, familia):
    fam = repo.get_familia(familia)
    return {a["nome"]: str(a["id"]) for a in fam["atributos"]}


def _criar(nome="Cabo", marca="Sil", familia_id=None, dados=None, atributos=None):
    return repo.create_product(
        familia_id=familia_id, nome=nome, marca=marca, descricao="",
        categoria="Eletrica",
        dados=dados or {"sku": "SKU", "preco": 10.0},
        atributos=atributos,
    )


def test_get_product_le_atributos_do_jsonb(system_db, familia, attr_ids):
    pid = _criar(
        familia_id=familia,
        dados={"sku": "SKU-JB", "ean": "7891", "preco": 10.0},
        atributos={"Bitola": "2,5mm", "Cor": "Verde"},
    )
    prod = repo.get_product(pid)
    assert prod["atributos"] == {"Bitola": "2,5mm", "Cor": "Verde"}
    # `atributos_nomes` espelha o mesmo conteúdo (chaves por nome).
    assert prod["atributos_nomes"] == {"Bitola": "2,5mm", "Cor": "Verde"}


def test_get_product_atributos_vazios(system_db):
    pid = _criar(dados={"sku": "SKU-SEM", "preco": 10.0})
    prod = repo.get_product(pid)
    assert prod["atributos"] == {}


# ---------------------------------------------------------------------------
# Marcas: create-or-get + vínculo marca_id
# ---------------------------------------------------------------------------

def test_marcas_resolver_create_or_get(system_db):
    with system_conn() as conn:
        mid1 = marcas_repo.resolver(conn, "Corfio")
        mid2 = marcas_repo.resolver(conn, "Corfio")
        mid3 = marcas_repo.resolver(conn, "  Sil  ")
        assert mid1 == mid2
        assert mid3 != mid1
        assert marcas_repo.resolver(conn, "") is None
        nomes = {m["nome"] for m in marcas_repo.listar(conn)}
    assert nomes == {"Corfio", "Sil"}


def test_create_product_vincula_marca_id(system_db):
    pid = _criar(nome="Cabo", marca="Corfio", dados={"sku": "SKU-MC", "preco": 10.0})
    prod = repo.get_product(pid)
    assert prod["marca"] == "Corfio"
    assert prod["marca_id"] is not None
    with system_conn() as conn:
        mid = conn.execute(
            "SELECT id FROM marcas WHERE nome='Corfio'"
        ).fetchone()[0]
    assert prod["marca_id"] == mid


def test_update_product_reusa_marca_existente(system_db):
    pid = _criar(nome="Cabo", marca="Corfio", dados={"sku": "SKU-UM", "preco": 10.0})
    repo.update_product(
        pid, None, "Cabo Atualizado", "Corfio", "", "Eletrica",
        dados={"sku": "SKU-UM", "preco": 10.0},
    )
    with system_conn() as conn:
        n = conn.execute("SELECT COUNT(*) FROM marcas").fetchone()[0]
    assert n == 1  # Corfio não duplicada


def test_marcas_api_rota_registrada(system_db):
    from flask import Flask

    from catalog_server.blueprints.api_produtos import api_produtos_bp

    app = Flask(__name__)
    app.register_blueprint(api_produtos_bp)
    reglas = {r.rule for r in app.url_map.iter_rules()}
    assert "/api/marcas" in reglas


# ---------------------------------------------------------------------------
# Geração/validação de SKUs em lote (interface de cadastro)
# ---------------------------------------------------------------------------

def test_gerar_lote_preenche_skus_vazios(system_db):
    from catalog_server.services import sku_service

    out = sku_service.gerar_lote("Cabo flexivel", [
        {"sku": ""},
        {"sku": ""},
    ], produto_id=0, conn=None)
    assert [o["sku"] for o in out] == ["CABO-FLEXIVEL-1", "CABO-FLEXIVEL-2"]
    assert all(o["aviso"] for o in out)


def test_gerar_lote_mantem_skus_validos_sem_aviso(system_db):
    from catalog_server.services import sku_service

    out = sku_service.gerar_lote("Cabo", [
        {"sku": "ABC-1"},
        {"sku": ""},
    ], produto_id=7, conn=None)
    assert out[0]["sku"] == "ABC-1"
    assert not out[0]["aviso"]
    assert out[1]["sku"] == "CABO-7-2"
    assert out[1]["aviso"]


def test_gerar_lote_sufixa_duplicado_no_lote(system_db):
    from catalog_server.services import sku_service

    out = sku_service.gerar_lote("Cabo", [
        {"sku": "DUP"},
        {"sku": "dup"},
    ], produto_id=0, conn=None)
    assert out[0]["sku"] == "DUP"
    assert out[1]["sku"] == "DUP-2"
    assert out[1]["aviso"]


def test_gerar_lote_invalido_retorna_vazio_e_aviso(system_db):
    from catalog_server.services import sku_service

    out = sku_service.gerar_lote("Cabo", [
        {"sku": "sku com espaco"},
    ], produto_id=0, conn=None)
    assert out[0]["sku"] == ""
    assert "esp" in out[0]["aviso"].lower() or out[0]["aviso"]


def test_gerar_lote_respeita_sku_ja_no_banco(system_db):
    from catalog_server.services import sku_service

    pid = _criar(dados={"sku": "JABULANI", "preco": 10.0})
    out = sku_service.gerar_lote("Cabo", [
        {"sku": "JABULANI"},
        {"sku": ""},
    ], produto_id=pid, conn=None)
    assert out[0]["sku"] == "JABULANI-2"
    assert out[1]["sku"] == f"CABO-{pid}-2"
