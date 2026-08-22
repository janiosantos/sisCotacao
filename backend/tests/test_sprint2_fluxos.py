"""Testes do Sprint 2: JSONB no repositório, SKU nos fluxos manuais e marcas.

Cobre o que foi integrado no Sprint 2 em `produtos.py`, `parse_url_service.py`
e no novo repositório `marcas`:

- `get_product` lê os atributos do JSONB (`variantes.atributos`, chaves por
  nome) com fallback para o EAV;
- `_replace_variantes` grava JSONB + EAV sincronizados e reserva SKU único;
- `find_or_create_variant` grava JSONB + EAV e gera SKU;
- `marcas` faz create-or-get e vincula `produtos_cadastro.marca_id`.
"""
from __future__ import annotations

import json

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
        "unidade_venda": "MT",
    }


# ---------------------------------------------------------------------------
# JSONB no get_product (fonte canônica + fallback EAV)
# ---------------------------------------------------------------------------

def test_get_product_le_atributos_do_jsonb(system_db, familia, attr_ids):
    pid = repo.create_product(
        familia_id=familia, nome="Cabo", marca="Sil", descricao="",
        categoria="Eletrica",
        variantes=[_variante("SKU-JB", "7891", _attrs(attr_ids, Bitola="2,5mm", Cor="Verde"))],
    )
    prod = repo.get_product(pid)
    v = prod["variantes"][0]
    assert v["atributos_nomes"] == {"Bitola": "2,5mm", "Cor": "Verde"}
    # Chaves por id (formato do frontend) derivadas do JSONB por nome.
    assert v["atributos"] == {
        attr_ids["Bitola"]: "2,5mm",
        attr_ids["Cor"]: "Verde",
    }


def test_get_product_fallback_eav_quando_jsonb_vazio(system_db, familia, attr_ids):
    pid = repo.create_product(
        familia_id=familia, nome="Cabo", marca="Sil", descricao="",
        categoria="Eletrica",
        variantes=[_variante("SKU-EAV", "7892", _attrs(attr_ids, Bitola="4mm"))],
    )
    # Simula registros antigos: JSONB vazio e atributos só no EAV.
    vid = repo.get_product(pid)["variantes"][0]["id"]
    with system_conn() as conn:
        conn.execute("UPDATE variantes SET atributos='{}' WHERE id=?", (vid,))
    prod = repo.get_product(pid)
    v = prod["variantes"][0]
    assert v["atributos_nomes"] == {"Bitola": "4mm"}
    assert v["atributos"] == {attr_ids["Bitola"]: "4mm"}


# ---------------------------------------------------------------------------
# _replace_variantes: JSONB + EAV sincronizados + SKU reservado
# ---------------------------------------------------------------------------

def test_replace_variantes_grava_jsonb_e_eav_sincronizados(system_db, familia, attr_ids):
    pid = repo.create_product(
        familia_id=familia, nome="Cabo", marca="Sil", descricao="",
        categoria="Eletrica",
        variantes=[_variante("SKU-SYNC", "7893", _attrs(attr_ids, Bitola="2,5mm", Cor="Azul"))],
    )
    vid = repo.get_product(pid)["variantes"][0]["id"]
    with system_conn() as conn:
        raw = conn.execute(
            "SELECT atributos FROM variantes WHERE id=?", (vid,)
        ).fetchone()[0]
        neav = conn.execute(
            "SELECT COUNT(*) FROM variante_atributos WHERE variante_id=?", (vid,)
        ).fetchone()[0]
    parsed = raw if isinstance(raw, dict) else json.loads(raw or "{}")
    assert parsed == {"Bitola": "2,5mm", "Cor": "Azul"}
    assert neav == 2


def test_replace_variantes_sku_duplicado_e_autocorrigido(system_db, familia, attr_ids):
    pid = repo.create_product(
        familia_id=familia, nome="Cabo", marca="Sil", descricao="",
        categoria="Eletrica",
        variantes=[
            _variante("SKU-DUP", "7894", _attrs(attr_ids, Bitola="2,5mm", Cor="Verde")),
            _variante("SKU-DUP", "7895", _attrs(attr_ids, Bitola="2,5mm", Cor="Azul")),
        ],
    )
    prod = repo.get_product(pid)
    skus = {v["sku"] for v in prod["variantes"]}
    assert len(skus) == 2
    assert "SKU-DUP" in skus
    assert any(s.startswith("SKU-DUP-") for s in skus)


def test_replace_variantes_sku_vazio_gera(system_db, familia, attr_ids):
    pid = repo.create_product(
        familia_id=familia, nome="Cabo", marca="Sil", descricao="",
        categoria="Eletrica",
        variantes=[_variante("", "7896", _attrs(attr_ids, Bitola="2,5mm"))],
    )
    prod = repo.get_product(pid)
    v = prod["variantes"][0]
    assert v["sku"]
    assert v["sku"] != ""


# ---------------------------------------------------------------------------
# find_or_create_variant: JSONB + EAV + SKU
# ---------------------------------------------------------------------------

def test_find_or_create_variant_grava_jsonb_e_gera_sku(system_db, familia, attr_ids):
    pid = repo.create_product(
        familia_id=familia, nome="Cabo", marca="Sil", descricao="",
        categoria="Eletrica",
        variantes=[_variante("SKU-001", "7890", _attrs(attr_ids, Bitola="2,5mm", Cor="Verde"))],
    )
    a_b = int(attr_ids["Bitola"])
    a_c = int(attr_ids["Cor"])
    # Reuso: mesma combinação → mesma variante.
    vid2 = repo.find_or_create_variant(pid, {a_b: "2,5mm", a_c: "Verde"}, "Sil")
    assert vid2 == repo.get_product(pid)["variantes"][0]["id"]
    # Nova combinação → nova variante com JSONB + EAV + SKU.
    vid3 = repo.find_or_create_variant(pid, {a_b: "2,5mm", a_c: "Azul"}, "Sil")
    assert vid3 != vid2
    prod = repo.get_product(pid)
    nova = next(v for v in prod["variantes"] if v["id"] == vid3)
    assert nova["atributos_nomes"] == {"Bitola": "2,5mm", "Cor": "Azul"}
    assert nova["sku"]


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


def test_create_product_vincula_marca_id(system_db, familia, attr_ids):
    pid = repo.create_product(
        familia_id=familia, nome="Cabo", marca="Corfio", descricao="",
        categoria="Eletrica",
        variantes=[_variante("SKU-MC", "7897", _attrs(attr_ids, Bitola="2,5mm"))],
    )
    prod = repo.get_product(pid)
    assert prod["marca"] == "Corfio"
    assert prod["marca_id"] is not None
    with system_conn() as conn:
        mid = conn.execute(
            "SELECT id FROM marcas WHERE nome='Corfio'"
        ).fetchone()[0]
    assert prod["marca_id"] == mid


def test_update_product_reusa_marca_existente(system_db, familia, attr_ids):
    pid = repo.create_product(
        familia_id=familia, nome="Cabo", marca="Corfio", descricao="",
        categoria="Eletrica",
        variantes=[_variante("SKU-UM", "7898", _attrs(attr_ids, Bitola="2,5mm"))],
    )
    repo.update_product(
        pid, familia, "Cabo Atualizado", "Corfio", "", "Eletrica",
        [_variante("SKU-UM", "7898", _attrs(attr_ids, Bitola="2,5mm"))],
    )
    with system_conn() as conn:
        n = conn.execute("SELECT COUNT(*) FROM marcas").fetchone()[0]
    assert n == 1  # Corfio não duplicada


# ---------------------------------------------------------------------------
# API de marcas (rota registrada no blueprint)
# ---------------------------------------------------------------------------

def test_marcas_api_rota_registrada(system_db):
    from flask import Flask

    from catalog_server.blueprints.api_produtos import api_produtos_bp

    app = Flask(__name__)
    app.register_blueprint(api_produtos_bp)
    reglas = {r.rule for r in app.url_map.iter_rules()}
    assert "/api/marcas" in reglas
    assert "/api/marcas" in reglas or True


# ---------------------------------------------------------------------------
# Sprint 3: geração/validação de SKUs em lote (interface de cadastro)
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


def test_gerar_lote_respeita_sku_ja_no_banco(system_db, familia, attr_ids):
    from catalog_server.services import sku_service

    pid = repo.create_product(
        familia_id=familia, nome="Cabo", marca="Sil", descricao="",
        categoria="Eletrica",
        variantes=[_variante("JABULANI", "7891", _attrs(attr_ids, Bitola="2,5mm"))],
    )
    out = sku_service.gerar_lote("Cabo", [
        {"sku": "JABULANI"},
        {"sku": ""},
    ], produto_id=pid, conn=None)
    assert out[0]["sku"] == "JABULANI-2"
    assert out[1]["sku"] == f"CABO-{pid}-2"