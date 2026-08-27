"""Perfil fiscal por variante: persistência, busca de NCM e API protegida."""
from __future__ import annotations

import uuid

import pytest

from catalog_server import auth_token
from catalog_server.repositories import fiscal_perfil
from catalog_server.db import system_conn


@pytest.fixture()
def variante_id():
    """Cria produto mínimo para o perfil (SKU único por execução)."""
    sufixo = uuid.uuid4().hex[:8]
    with system_conn() as conn:
        vid = conn.execute(
            "INSERT INTO produtos_cadastro (nome, sku) VALUES (?, ?)",
            ("PROD PERFIL TESTE", f"PERFIL-{sufixo}"),
        ).lastrowid
        conn.commit()
    return int(vid)


def test_perfil_ausente_retorna_vazio(variante_id):
    p = fiscal_perfil.obter(variante_id)
    assert p is None


def test_salvar_e_obter_perfil(variante_id):
    salvo = fiscal_perfil.salvar(
        variante_id,
        {"ncm": "8544.42.00", "cest": "28.001.00", "origem": 2,
         "regime_st": "", "fonte_url": "https://portalnfe/example"},
    )
    assert salvo["ncm"] == "8544.42.00"
    assert salvo["origem"] == 2

    # Atualização (upsert)
    fiscal_perfil.salvar(variante_id, {"ncm": "8544.42.00", "cest": "", "origem": 1})
    p = fiscal_perfil.obter(variante_id)
    assert p["origem"] == 1
    assert p["cest"] == ""


def test_buscar_ncm_registrada():
    dados = {"codigo": "9999.99.99", "descricao": "NCM de teste CI",
             "fonte_url": "https://portalnfe/teste", "vigencia_inicio": "2026-01-01"}
    novo = fiscal_perfil.registrar_ncm(dados)
    assert novo > 0
    res = fiscal_perfil.buscar_ncm("9999.99")
    assert any(r["codigo"] == "9999.99.99" for r in res)
    # Re-registro com MESMA vigência atualiza em vez de duplicar;
    # vigência diferente cria nova versão (UNIQUE codigo+vigencia_inicio).
    mesmo = fiscal_perfil.registrar_ncm({**dados, "descricao": "NCM de teste CI v2"})
    assert mesmo == novo
    outra = fiscal_perfil.registrar_ncm(
        {**dados, "vigencia_inicio": "2027-01-01", "descricao": "versão futura"}
    )
    assert outra != novo


def test_api_perfil_protegida_e_funcional(app_client_token, variante_id):
    c, H = app_client_token
    r = c.get(f"/api/fiscal/perfil/{variante_id}", headers=H)
    assert r.status_code == 200
    r2 = c.put(
        f"/api/fiscal/perfil/{variante_id}",
        headers=H,
        json={"ncm": "1234.56.78", "origem": 0},
    )
    assert r2.status_code == 200 and r2.get_json()["ncm"] == "1234.56.78"


def test_api_sem_token_bloqueada(app_client_token):
    c, _ = app_client_token
    import flask
    r = c.get("/api/fiscal/perfil/1", headers={})
    assert r.status_code in (302, 401)


@pytest.fixture()
def app_client_token():
    from catalog_server.app_factory import create_app

    app = create_app()
    c = app.test_client()
    tok = auth_token.criar_token({"id": 1, "login": "t", "perfil": "admin"})
    return c, {"Authorization": f"Bearer {tok}"}
