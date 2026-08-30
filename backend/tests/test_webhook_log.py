"""Log de webhooks + rechecagem em lotes (migração 0100)."""
from __future__ import annotations

import time
from unittest.mock import patch

from werkzeug.security import generate_password_hash

from catalog_server import auth_token, permissao
from catalog_server.app_factory import create_app
from catalog_server.db import system_conn
from catalog_server.payments.repo import payment_provider_repo


def _client_admin():
    with system_conn() as conn:
        uid = int(conn.execute(
            "INSERT INTO usuarios (login, nome, senha_hash) VALUES (%s,%s,%s) RETURNING id",
            ("admwhl", "Adm Wh Log", generate_password_hash("x")),
        ).fetchone()["id"])
        pid = int(conn.execute("SELECT id FROM perfis WHERE nome='Administrador'").fetchone()["id"])
        conn.execute(
            "INSERT INTO usuario_perfis (usuario_id, perfil_id) VALUES (%s,%s) ON CONFLICT DO NOTHING",
            (uid, pid),
        )
        conn.commit()
    permissao.invalidar(uid)
    c = create_app().test_client()
    h = {"Authorization": f"Bearer {auth_token.criar_token({'id': uid, 'login': 'admwhl'})}"}
    return c, h


def _cfg(codigo: str, nome: str, secret: str):
    with system_conn() as conn:
        conn.execute(
            "INSERT INTO payment_provider (codigo, nome) VALUES (%s,%s) ON CONFLICT (codigo) DO NOTHING",
            (codigo, nome),
        )
        pid = int(conn.execute("SELECT id FROM payment_provider WHERE codigo=%s", (codigo,)).fetchone()["id"])
        conn.commit()
    payment_provider_repo.upsert_config({
        "provider_id": pid, "operacao": "pix", "ambiente": "sandbox",
        "webhook_secret": secret, "prioridade": 1, "ativo": 1,
    })


def _conta(payment_id: str, provider_codigo: str = "mercadopago") -> int:
    from catalog_server.repositories import cliente_repo, contas_repo

    cliente_repo.garantir_padrao()
    with system_conn() as conn:
        conn.execute("SELECT setval('clientes_id_seq', GREATEST((SELECT COALESCE(MAX(id),1) FROM clientes),1))")
        conn.commit()
    cid = cliente_repo.create({"nome": "Wh Log", "tipo_pessoa": "f", "doc": "12345678909"})
    conta_id = contas_repo.criar_receber(cliente="Wh Log", cliente_id=cid, valor=88.0,
                                         data_vencimento="2026-12-31", descricao="Wh Log")
    with system_conn() as conn:
        pid = conn.execute("SELECT id FROM payment_provider WHERE codigo=%s", (provider_codigo,)).fetchone()["id"]
        conn.execute(
            "UPDATE contas_receber SET payment_id=%s, provider_id=%s, tipo_cobranca='pix',"
            " ambiente_cobranca='sandbox', status_cobranca='pendente' WHERE id=%s",
            (payment_id, pid, conta_id),
        )
        conn.commit()
    return conta_id


def test_webhook_registra_log_processado(system_db):
    _cfg("asaas", "Asaas", "wh_log_secret")
    c, _ = _client_admin()
    payload = {"event": "PAYMENT_RECEIVED", "payment": {"id": "pay_log_1", "value": 88.0}}
    r = c.post("/api/webhooks/payments/asaas", json=payload,
               headers={"asaas-access-token": "wh_log_secret"})
    assert r.status_code == 200
    with system_conn() as conn:
        row = conn.execute(
            "SELECT provider, status, payment_id, evento, assinatura_ok, http_status"
            " FROM webhook_log WHERE payment_id='pay_log_1' ORDER BY id DESC LIMIT 1"
        ).fetchone()
    assert row is not None
    assert row["provider"] == "asaas"
    assert row["status"] in ("ignorado", "processado")
    assert row["evento"] == "PAYMENT_RECEIVED"
    assert row["assinatura_ok"] is True
    assert row["http_status"] == 200


def test_webhook_nao_autorizado_registra_log(system_db):
    _cfg("asaas", "Asaas", "wh_log_secret")
    c, _ = _client_admin()
    payload = {"event": "PAYMENT_RECEIVED", "payment": {"id": "pay_log_2"}}
    r = c.post("/api/webhooks/payments/asaas", json=payload, headers={"asaas-access-token": "errado"})
    assert r.status_code == 401
    with system_conn() as conn:
        row = conn.execute(
            "SELECT status, http_status FROM webhook_log"
            " WHERE payment_id='pay_log_2' AND status='nao_autorizado' ORDER BY id DESC LIMIT 1"
        ).fetchone()
    assert row is not None
    assert row["http_status"] == 401


def test_listar_logs_e_detalhe(system_db):
    _cfg("asaas", "Asaas", "wh_log_secret")
    c, h = _client_admin()
    c.post("/api/webhooks/payments/asaas",
           json={"event": "PAYMENT_RECEIVED", "payment": {"id": "pay_log_3"}},
           headers={"asaas-access-token": "wh_log_secret"})
    r = c.get("/api/webhooks/logs?provider=asaas", headers=h)
    assert r.status_code == 200
    data = r.get_json()
    assert data["total"] >= 1
    assert any(i["payment_id"] == "pay_log_3" for i in data["items"])
    log_id = next(i["id"] for i in data["items"] if i["payment_id"] == "pay_log_3")
    r2 = c.get(f"/api/webhooks/logs/{log_id}", headers=h)
    assert r2.status_code == 200
    assert r2.get_json()["payment_id"] == "pay_log_3"


def test_rechecagem_baixa_conta_paga(system_db):
    from catalog_server.services import webhook_log

    _cfg("mercadopago", "Mercado Pago", "wh_log_mp")
    conta_id = _conta("pay_recheck_1")
    with patch("catalog_server.payments.mercadopago.MercadoPagoProvider.consultar",
               return_value={"status_cobranca": "pago"}):
        res = webhook_log.rechecagem(provider="mercadopago")
    assert res["verificadas"] >= 1
    assert res["pagas"] >= 1
    with system_conn() as conn:
        row = conn.execute("SELECT status, saldo FROM contas_receber WHERE id=%s", (conta_id,)).fetchone()
    assert row["status"] == "pago"
    assert float(row["saldo"]) == 0