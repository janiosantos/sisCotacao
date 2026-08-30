"""Validação de assinatura/token nativo dos webhooks de pagamento (P2).

Cobre: Mercado Pago (x-signature HMAC + anti-replay por ts), Asaas
(asaas-access-token), EfiPay (token em query/header), idempotência por evento
(repetido não baixa 2x) e fail-safe em produção sem segredo.
"""
from __future__ import annotations

import hashlib
import hmac
import time
from unittest.mock import patch

from werkzeug.security import generate_password_hash

from catalog_server import auth_token, permissao
from catalog_server.app_factory import create_app
from catalog_server.db import system_conn
from catalog_server.payments.repo import payment_provider_repo


def _perfil_admin() -> int:
    with system_conn() as conn:
        return int(conn.execute("SELECT id FROM perfis WHERE nome='Administrador'").fetchone()["id"])


def _client_admin():
    with system_conn() as conn:
        uid = int(conn.execute(
            "INSERT INTO usuarios (login, nome, senha_hash) VALUES (%s,%s,%s) RETURNING id",
            ("admwh", "Adm Webhook", generate_password_hash("x")),
        ).fetchone()["id"])
        conn.execute(
            "INSERT INTO usuario_perfis (usuario_id, perfil_id) VALUES (%s,%s) ON CONFLICT DO NOTHING",
            (uid, _perfil_admin()),
        )
        conn.commit()
    permissao.invalidar(uid)
    c = create_app().test_client()
    h = {"Authorization": f"Bearer {auth_token.criar_token({'id': uid, 'login': 'admwh'})}"}
    return c, h


def _provider_cfg(codigo: str, nome: str, webhook_secret: str, **extra):
    with system_conn() as conn:
        conn.execute(
            "INSERT INTO payment_provider (codigo, nome) VALUES (%s,%s) ON CONFLICT (codigo) DO NOTHING",
            (codigo, nome),
        )
        pid = int(conn.execute("SELECT id FROM payment_provider WHERE codigo=%s", (codigo,)).fetchone()["id"])
        conn.commit()
    dados = {
        "provider_id": pid,
        "operacao": "pix",
        "ambiente": "sandbox",
        "webhook_secret": webhook_secret,
        "prioridade": 1,
        "ativo": 1,
    }
    dados.update(extra)
    payment_provider_repo.upsert_config(dados)


def _conta_pix(payment_id: str, valor: float = 500.0) -> int:
    from catalog_server.repositories import cliente_repo, contas_repo

    cliente_repo.garantir_padrao()
    with system_conn() as conn:
        conn.execute(
            "SELECT setval('clientes_id_seq', GREATEST((SELECT COALESCE(MAX(id),1) FROM clientes), 1))"
        )
        conn.commit()
    cid = cliente_repo.create({"nome": "Wh Teste", "tipo_pessoa": "f", "doc": "98765432100", "limite_credito": 5000})
    conta_id = contas_repo.criar_receber(
        cliente="Wh Teste", cliente_id=cid, valor=valor,
        data_vencimento="2026-12-31", descricao="Webhook",
    )
    with system_conn() as conn:
        conn.execute(
            "UPDATE contas_receber SET payment_id=%s, tipo_cobranca='pix', "
            "ambiente_cobranca='sandbox', status_cobranca='pendente', status='aberto' WHERE id=%s",
            (payment_id, conta_id),
        )
        conn.commit()
    return conta_id


def _mp_signature(secret: str, data_id: str, ts_ms: str | None = None, x_req: str = "req-1") -> str:
    ts = ts_ms or str(int(time.time() * 1000))
    manifest = f"id:{data_id};request-id:{x_req};ts:{ts};"
    v1 = hmac.new(secret.encode(), manifest.encode(), hashlib.sha256).hexdigest()
    return f"ts={ts},v1={v1}"


# ─── Mercado Pago ─────────────────────────────────────────────


def test_mp_assinatura_valida_baixa_conta(system_db):
    c, h = _client_admin()
    _provider_cfg("mercadopago", "Mercado Pago", "mp_secret", access_token="TEST_MP")
    conta_id = _conta_pix("pay_mp_1")
    data_id = "pay_mp_1"
    x_sig = _mp_signature("mp_secret", data_id)
    payload = {"type": "payment", "data": {"id": data_id}}
    with patch("catalog_server.payments.mercadopago.MercadoPagoProvider.consultar",
               return_value={"status_cobranca": "pago"}):
        r = c.post("/api/webhooks/payments/mercadopago", json=payload,
                   query_string={"data.id": data_id, "type": "payment"},
                   headers={"x-signature": x_sig, "x-request-id": "req-1"})
    assert r.status_code == 200, r.get_json()
    with system_conn() as conn:
        row = conn.execute("SELECT status, saldo, webhook_id FROM contas_receber WHERE id=%s", (conta_id,)).fetchone()
    assert row["status"] == "pago"
    assert float(row["saldo"]) == 0
    assert row["webhook_id"] == f"payment:{data_id}"


def test_mp_assinatura_invalida_401(system_db):
    c, h = _client_admin()
    _provider_cfg("mercadopago", "Mercado Pago", "mp_secret", access_token="TEST_MP")
    _conta_pix("pay_mp_2")
    payload = {"type": "payment", "data": {"id": "pay_mp_2"}}
    x_sig = _mp_signature("SEGREDO_ERRADO", "pay_mp_2")
    r = c.post("/api/webhooks/payments/mercadopago", json=payload,
               query_string={"data.id": "pay_mp_2"},
               headers={"x-signature": x_sig, "x-request-id": "req-1"})
    assert r.status_code == 401
    with system_conn() as conn:
        row = conn.execute("SELECT status FROM contas_receber WHERE payment_id='pay_mp_2'").fetchone()
    assert row["status"] != "pago"


def test_mp_replay_ts_antigo_401(system_db):
    c, h = _client_admin()
    _provider_cfg("mercadopago", "Mercado Pago", "mp_secret", access_token="TEST_MP")
    _conta_pix("pay_mp_3")
    ts_antigo = str(int(time.time() * 1000) - 3600 * 1000)  # 1h atrás (janela=5min)
    x_sig = _mp_signature("mp_secret", "pay_mp_3", ts_ms=ts_antigo)
    payload = {"type": "payment", "data": {"id": "pay_mp_3"}}
    r = c.post("/api/webhooks/payments/mercadopago", json=payload,
               query_string={"data.id": "pay_mp_3"},
               headers={"x-signature": x_sig, "x-request-id": "req-1"})
    assert r.status_code == 401  # replay/payload antigo rejeitado


# ─── Asaas ────────────────────────────────────────────────────


def test_asaas_token_correto_processa_e_duplicado_nao_baixa_2x(system_db):
    c, h = _client_admin()
    _provider_cfg("asaas", "Asaas", "auth_token_asaas", api_key="TESTE_API")
    conta_id = _conta_pix("pay_asaas")
    payload = {"event": "PAYMENT_RECEIVED", "payment": {"id": "pay_asaas", "value": 500.0}}
    r = c.post("/api/webhooks/payments/asaas", json=payload,
               headers={"asaas-access-token": "auth_token_asaas"})
    assert r.status_code == 200, r.get_json()
    assert r.get_json()["ok"] is True
    with system_conn() as conn:
        row = conn.execute("SELECT status, saldo FROM contas_receber WHERE id=%s", (conta_id,)).fetchone()
    assert row["status"] == "pago"
    # repetido: idempotente, não baixa de novo nem duplica caixa
    r2 = c.post("/api/webhooks/payments/asaas", json=payload,
                headers={"asaas-access-token": "auth_token_asaas"})
    assert r2.status_code == 200
    assert r2.get_json().get("duplicado") is True
    with system_conn() as conn:
        row2 = conn.execute("SELECT status, saldo FROM contas_receber WHERE id=%s", (conta_id,)).fetchone()
    assert row2["status"] == "pago"
    assert float(row2["saldo"]) == 0


def test_asaas_token_errado_401(system_db):
    c, h = _client_admin()
    _provider_cfg("asaas", "Asaas", "auth_token_asaas", api_key="TESTE_API")
    _conta_pix("pay_asaas2")
    payload = {"event": "PAYMENT_RECEIVED", "payment": {"id": "pay_asaas2"}}
    r = c.post("/api/webhooks/payments/asaas", json=payload,
               headers={"asaas-access-token": "errado"})
    assert r.status_code == 401


# ─── EfiPay ───────────────────────────────────────────────────


def test_efipay_token_query_valido_baixa(system_db):
    c, h = _client_admin()
    _provider_cfg("efipay", "EfiPay", "token_efi", client_id="c", client_secret="s")
    _conta_pix("txid_efi")
    payload = {"type": "pix.received", "pix": {"txid": "txid_efi", "valor": "500.00"}}
    r = c.post("/api/webhooks/payments/efipay", json=payload,
               query_string={"token": "token_efi"})
    assert r.status_code == 200, r.get_json()
    with system_conn() as conn:
        row = conn.execute("SELECT status FROM contas_receber WHERE payment_id='txid_efi'").fetchone()
    assert row["status"] == "pago"


def test_efipay_token_errado_401(system_db):
    c, h = _client_admin()
    _provider_cfg("efipay", "EfiPay", "token_efi", client_id="c", client_secret="s")
    _conta_pix("txid_efi2")
    payload = {"type": "pix.received", "pix": {"txid": "txid_efi2"}}
    r = c.post("/api/webhooks/payments/efipay", json=payload,
               query_string={"token": "errado"})
    assert r.status_code == 401


# ─── Fail-safe em produção ────────────────────────────────────


def test_producao_sem_segredo_rejeita(system_db, monkeypatch):
    c, h = _client_admin()
    _provider_cfg("sicoob", "Sicoob", "")  # sem webhook_secret
    _conta_pix("pix_sicoob")
    payload = {"pix": [{"txid": "pix_sicoob", "valor": "500.00"}]}
    monkeypatch.setenv("CATALOG_ENV", "production")
    monkeypatch.delenv("PAYMENT_WEBHOOK_SECRET", raising=False)
    r = c.post("/api/webhooks/payments/sicoob", json=payload)
    assert r.status_code == 401  # fail-safe: sem segredo em produção


def test_producao_com_segredo_generico_aceita(system_db, monkeypatch):
    c, h = _client_admin()
    _provider_cfg("sicoob", "Sicoob", "segredo_sicoob")
    _conta_pix("pix_sicoob2")
    payload = {"pix": [{"txid": "pix_sicoob2", "valor": "500.00"}]}
    monkeypatch.setenv("CATALOG_ENV", "production")
    r = c.post("/api/webhooks/payments/sicoob", json=payload,
               headers={"X-Webhook-Secret": "segredo_sicoob"})
    assert r.status_code == 200, r.get_json()