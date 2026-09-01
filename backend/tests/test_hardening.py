"""Regressões de segurança e consistência introduzidas pelo hardening."""
from __future__ import annotations

import uuid

import pytest

from catalog_server import auth_token
from catalog_server.db import system_conn
from catalog_server.repositories import estoque_repo
from catalog_server.payments.repo import payment_provider_repo
from catalog_server.app_factory import create_app


def _produto_deposito() -> tuple[int, int]:
    sufixo = uuid.uuid4().hex[:8]
    with system_conn() as conn:
        deposito = conn.execute(
            "INSERT INTO depositos (nome) VALUES (?) RETURNING id",
            (f"DEP HARDENING {sufixo}",),
        ).fetchone()["id"]
        produto = conn.execute(
            "INSERT INTO produtos_cadastro (nome, sku) VALUES (?, ?) RETURNING id",
            ("PROD HARDENING", f"HARD-{sufixo}"),
        ).fetchone()["id"]
    return int(deposito), int(produto)


def test_fato_rejeita_saida_acima_do_disponivel(system_db):
    deposito, produto = _produto_deposito()
    estoque_repo.movimentar_fato(deposito, produto, "entrada", 2)

    with pytest.raises(ValueError, match="insuficiente"):
        estoque_repo.movimentar_fato(deposito, produto, "saida", 3)

    saldo = estoque_repo.saldo(deposito_id=deposito, produto_id=produto)[0]
    assert float(saldo["quantidade"]) == 2


def test_configuracao_de_pagamento_nao_retorna_segredos(system_db):
    with system_conn() as conn:
        provider_id = conn.execute(
            "INSERT INTO payment_provider (codigo, nome) VALUES (?, ?) RETURNING id",
            ("hardening", "Hardening"),
        ).fetchone()["id"]
        conn.execute(
            "INSERT INTO payment_provider_config"
            " (provider_id, operacao, ambiente, client_secret, api_key)"
            " VALUES (?, 'pix', 'sandbox', 'segredo', 'chave')",
            (provider_id,),
        )

    configs = payment_provider_repo.list_configs()
    config = next(c for c in configs if c["provider_codigo"] == "hardening")
    assert config["credencial_configurada"] is True
    assert "client_secret" not in config
    assert "api_key" not in config


def test_usuario_inativo_nao_acessa_api(system_db):
    from werkzeug.security import generate_password_hash

    with system_conn() as conn:
        user_id = conn.execute(
            "INSERT INTO usuarios (nome, login, senha_hash, ativo)"
            " VALUES (?, ?, ?, 0) RETURNING id",
            ("Inativo", f"inativo-{uuid.uuid4().hex[:8]}", generate_password_hash("x123")),
        ).fetchone()["id"]

    token = auth_token.criar_token({"id": user_id, "login": "inativo"})
    response = create_app().test_client().get(
        "/api/produtos", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 401


def test_login_tem_rate_limit_distribuido(system_db):
    client = create_app().test_client()
    login = f"brute-{uuid.uuid4().hex[:8]}"

    for _ in range(5):
        response = client.post(
            "/api/login", json={"login": login, "senha": "incorreta"}
        )
        assert response.status_code == 401

    response = client.post(
        "/api/login", json={"login": login, "senha": "incorreta"}
    )
    assert response.status_code == 429
    assert response.headers["Retry-After"] == "300"
