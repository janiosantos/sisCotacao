"""Fatos de estoque: idempotência, reservas e reconciliação (ADR 0003)."""
from __future__ import annotations

import uuid

import pytest

from catalog_server import auth_token
from catalog_server.db import system_conn
from catalog_server.repositories import estoque_repo


@pytest.fixture()
def dep_var():
    sufixo = uuid.uuid4().hex[:8]
    with system_conn() as conn:
        did = conn.execute(
            "INSERT INTO depositos (nome) VALUES (?)",
            (f"DEP TESTE FATOS {sufixo}",),
        ).lastrowid
        pid = conn.execute(
            "INSERT INTO produtos_cadastro (nome, sku) VALUES (?, ?)",
            ('PROD FATOS', f"FATOS-{sufixo}"),
        ).lastrowid
        conn.commit()
    return int(did), int(pid)


@pytest.fixture()
def app_client_token():
    from catalog_server.app_factory import create_app

    app = create_app()
    c = app.test_client()
    tok = auth_token.criar_token({"id": 1, "login": "t", "perfil": "admin"})
    return c, {"Authorization": f"Bearer {tok}"}


def test_movimento_idempotente_retrida_ignora(dep_var):
    did, vid = dep_var
    key = f"entrada-teste-{uuid.uuid4().hex[:8]}"
    r1 = estoque_repo.movimentar_fato(
        did, vid, "entrada", 10, idempotency_key=key, origem_tipo="teste"
    )
    r2 = estoque_repo.movimentar_fato(
        did, vid, "entrada", 10, idempotency_key=key, origem_tipo="teste"
    )
    assert r1["duplicado"] is False
    assert r2["duplicado"] is True
    assert r1["movimento_id"] == r2["movimento_id"]
    saldo = estoque_repo.saldo(deposito_id=did, variante_id=vid)[0]
    assert float(saldo["quantidade"]) == 10.0  # não somou duas vezes


def test_reserva_e_liberacao_afetam_reserva(dep_var):
    did, vid = dep_var
    estoque_repo.movimentar_fato(did, vid, "entrada", 20)
    estoque_repo.movimentar_fato(did, vid, "reserva", 5)
    saldo = estoque_repo.saldo(deposito_id=did, variante_id=vid)[0]
    assert float(saldo["reserva"]) == 5.0
    assert float(saldo["quantidade"]) == 20.0
    estoque_repo.movimentar_fato(did, vid, "liberacao", 5)
    saldo = estoque_repo.saldo(deposito_id=did, variante_id=vid)[0]
    assert float(saldo["reserva"]) == 0.0


def test_reconciliacao_ok_apos_fatos(dep_var):
    did, vid = dep_var
    estoque_repo.movimentar_fato(did, vid, "entrada", 15)
    estoque_repo.movimentar_fato(did, vid, "saida", 4)
    rec = estoque_repo.reconciliar(did, vid)
    assert rec is not None


def test_api_movimentos_fato(app_client_token, dep_var):
    did, vid = dep_var
    c, H = app_client_token
    key = f"api-{uuid.uuid4().hex[:8]}"
    r1 = c.post(
        "/api/estoque/movimentos",
        headers=H,
        json={"deposito_id": did, "variante_id": vid, "tipo": "entrada",
              "quantidade": 7, "idempotency_key": key,
              "origem_tipo": "teste-api"},
    )
    assert r1.status_code == 201 and r1.get_json()["duplicado"] is False
    r2 = c.post(
        "/api/estoque/movimentos",
        headers=H,
        json={"deposito_id": did, "variante_id": vid, "tipo": "entrada",
              "quantidade": 7, "idempotency_key": key},
    )
    assert r2.status_code == 200 and r2.get_json()["duplicado"] is True


def test_api_sem_token_bloqueada():
    from catalog_server.app_factory import create_app

    c = create_app().test_client()
    r = c.post("/api/estoque/movimentos", json={})
    assert r.status_code in (302, 401)
