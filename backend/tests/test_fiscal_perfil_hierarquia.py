"""Hierarquia de perfil fiscal: produto default → override na variação."""
from __future__ import annotations

import uuid

import pytest

from catalog_server import auth_token
from catalog_server.db import system_conn
from catalog_server.repositories import fiscal_perfil


@pytest.fixture()
def prod_var():
    sufixo = uuid.uuid4().hex[:8]
    with system_conn() as conn:
        pid = conn.execute(
            "INSERT INTO produtos_cadastro (nome, sku) VALUES (?, ?)",
            ("PROD HIERARQUIA", f"HIER-{sufixo}"),
        ).lastrowid
        conn.commit()
    # No modelo unificado a "variação" é o próprio produto: o mesmo id serve
    # de produto (produto_fiscal_profile) e de override (product_fiscal_profile).
    return int(pid), int(pid)


@pytest.fixture()
def app_client_token(system_db):
    from catalog_server.app_factory import create_app
    from werkzeug.security import generate_password_hash

    with system_conn() as conn:
        cur = conn.execute(
            "INSERT INTO usuarios (nome, login, senha_hash) VALUES (%s,%s,%s) RETURNING id",
            ("Admin Fiscal H", "admin_fiscal_h", generate_password_hash("x")),
        )
        uid = int(cur.fetchone()["id"])
        conn.execute(
            "INSERT INTO usuario_perfis (usuario_id, perfil_id) SELECT %s, id FROM perfis WHERE nome='Administrador'",
            (uid,),
        )
        conn.commit()
    app = create_app()
    c = app.test_client()
    tok = auth_token.criar_token({"id": uid, "login": "admin_fiscal_h"})
    return c, {"Authorization": f"Bearer {tok}"}


def test_produto_default_e_override_sem_divergencia(prod_var):
    pid, vid = prod_var
    fiscal_perfil.salvar_produto(pid, {"ncm": "8544.42.00", "origem": 2})
    # variação sem NCM herda o padrão do produto na leitura combinada
    assert fiscal_perfil.obter_produto(pid)["ncm"] == "8544.42.00"
    fiscal_perfil.salvar(vid, {"ncm": "", "origem": 2})  # sem divergência


def test_override_divergente_exige_justificativa(prod_var):
    pid, vid = prod_var
    fiscal_perfil.salvar_produto(pid, {"ncm": "8544.42.00", "origem": 2})
    with pytest.raises(ValueError, match="justificativa"):
        fiscal_perfil.salvar_override_variante(
            vid, {"ncm": "9999.99.99"}, fiscal_perfil.obter_produto(pid)
        )
    ok = fiscal_perfil.salvar_override_variante(
        vid,
        {"ncm": "9999.99.99", "justificativa_override": "kit especial importado"},
        fiscal_perfil.obter_produto(pid),
    )
    assert ok["ncm"] == "9999.99.99"


def test_api_perfil_produto(app_client_token, prod_var):
    pid, _ = prod_var
    c, H = app_client_token
    r = c.put(
        f"/api/fiscal/perfil-produto/{pid}",
        headers=H,
        json={"ncm": "1111.11.11"},
    )
    assert r.status_code == 200 and r.get_json()["ncm"] == "1111.11.11"
    r2 = c.get(f"/api/fiscal/perfil-produto/{pid}", headers=H)
    assert r2.get_json()["ncm"] == "1111.11.11"
