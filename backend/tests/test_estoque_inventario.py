"""Inventário-fato e reconciliação automática (ADR 0003, gaps #3/#4)."""
from __future__ import annotations

import uuid

from catalog_server import auth_token
from catalog_server.db import system_conn
from catalog_server.repositories import estoque_repo


def _setup():
    sufixo = uuid.uuid4().hex[:8]
    with system_conn() as conn:
        did = conn.execute(
            "INSERT INTO depositos (nome) VALUES (?)",
            (f"DEP INV {sufixo}",),
        ).lastrowid
        pid = conn.execute(
            "INSERT INTO produtos_cadastro (nome, sku) VALUES (?, ?)",
            ('PROD INV', f"INV-{sufixo}"),
        ).lastrowid
        conn.commit()
    return int(did), int(pid)


def test_inventario_corrige_saldo_com_fato():
    did, vid = _setup()
    estoque_repo.movimentar_fato(did, vid, "entrada", 10)
    r = estoque_repo.lancar_inventario(
        did, vid, 12, justificativa="contagem: 12 no local",
        idempotency_key=f"inv-{uuid.uuid4().hex[:8]}",
    )
    assert r["duplicado"] is False and r["tipo"] == "inventario"
    saldo = estoque_repo.saldo(deposito_id=did, variante_id=vid)[0]
    assert float(saldo["quantidade"]) == 12.0


def test_inventario_sem_divergencia_nao_move():
    did, vid = _setup()
    estoque_repo.movimentar_fato(did, vid, "entrada", 7)
    r = estoque_repo.lancar_inventario(did, vid, 7, justificativa="ok")
    assert r["duplicado"] is True and r["movimento_id"] is None


def test_reconciliar_tudo_identifica_divergencia():
    did, vid = _setup()
    estoque_repo.movimentar_fato(did, vid, "entrada", 5)
    # força divergência: mexe direto no saldo materializado
    with system_conn() as conn:
        conn.execute(
            "UPDATE estoque_saldo SET quantidade=99 WHERE deposito_id=? AND produto_id=?",
            (did, vid),
        )
        conn.commit()
    div = estoque_repo.reconciliar_tudo(did)
    assert any(d["produto_id"] == vid for d in div)


def test_api_inventario():
    from catalog_server.app_factory import create_app

    app = create_app()
    c = app.test_client()
    tok = auth_token.criar_token({"id": 1, "login": "t", "perfil": "admin"})
    H = {"Authorization": f"Bearer {tok}"}
    did, vid = _setup()
    estoque_repo.movimentar_fato(did, vid, "entrada", 3)
    r = c.post(
        "/api/estoque/inventarios",
        headers=H,
        json={"deposito_id": did, "variante_id": vid,
              "quantidade_contada": 9, "justificativa": "conferência",
              "idempotency_key": f"api-inv-{uuid.uuid4().hex[:8]}"},
    )
    assert r.status_code == 201
    assert r.get_json()["tipo"] == "inventario"
