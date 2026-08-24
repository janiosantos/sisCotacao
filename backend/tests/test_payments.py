"""IntegraÃ§Ã£o de pagamentos nas contas a receber (v2.23.0, fase 1).

Cobre (com mock das APIs Asaas/Mercado Pago):
- configuraÃ§Ã£o de provedor (prioridade de custo);
- emissÃ£o de boleto e PIX grava na conta;
- webhook baixa automaticamente a conta (idempotente);
- recebimento manual com forma de pagamento (lanÃ§a caixa);
- comprovante de depÃ³sito/TED anexado.
"""
from __future__ import annotations

import io

from unittest.mock import patch

from catalog_server import auth_token
from catalog_server.db import system_conn
from catalog_server.app_factory import create_app


def _usuario(login: str) -> int:
    from werkzeug.security import generate_password_hash

    with system_conn() as conn:
        cur = conn.execute(
            "INSERT INTO usuarios (nome, login, senha_hash, desconto_limite_pct)"
            " VALUES (%s,%s,%s,5)",
            ("Financeiro", login, generate_password_hash("x123")),
        )
        uid = int(cur.lastrowid)
        conn.commit()
    return uid


def _perfil_id(nome: str) -> int:
    with system_conn() as conn:
        return int(conn.execute(
            "SELECT id FROM perfis WHERE nome=%s", (nome,)
        ).fetchone()["id"])


def _admin_client(system_db):
    uid = _usuario("admfin")
    from catalog_server import permissao

    with system_conn() as conn:
        conn.execute(
            "INSERT INTO usuario_perfis (usuario_id, perfil_id) VALUES (%s,%s) ON CONFLICT DO NOTHING",
            (uid, _perfil_id("Administrador")),
        )
        conn.commit()
    permissao.invalidar(uid)
    c = create_app().test_client()
    h = {"Authorization": f"Bearer {auth_token.criar_token({'id': uid, 'login': 'admfin'})}"}
    return c, h


def _config_asaas(system_db, operacao="boleto"):
    """Cria config Asaas sandbox com prioridade baixa."""
    from catalog_server.payments.repo import payment_provider_repo

    with system_conn() as conn:
        conn.execute(
            "INSERT INTO payment_provider (codigo, nome) VALUES ('asaas','Asaas')"
            " ON CONFLICT (codigo) DO NOTHING"
        )
        pid = int(conn.execute(
            "SELECT id FROM payment_provider WHERE codigo='asaas'"
        ).fetchone()["id"])
        conn.commit()
    payment_provider_repo.upsert_config({
        "provider_id": pid,
        "operacao": operacao,
        "ambiente": "sandbox",
        "api_key": "TESTE_API_KEY",
        "prioridade": 1,
        "ativo": 1,
    })


def _conta(system_db) -> int:
    from catalog_server.repositories import cliente_repo, contas_repo

    cliente_repo.garantir_padrao()
    with system_conn() as conn:
        conn.execute(
            "SELECT setval('clientes_id_seq', GREATEST((SELECT COALESCE(MAX(id),1) FROM clientes), 1))"
        )
        conn.commit()
    cid = cliente_repo.create({"nome": "Maria Teste", "tipo_pessoa": "f", "doc": "12345678909", "limite_credito": 5000})
    return contas_repo.criar_receber(
        cliente="Maria Teste",
        cliente_id=cid,
        valor=500.0,
        data_vencimento="2026-12-31",
        descricao="Parcela 1/2",
        documento="ORC0099",
    )


def test_configurar_provedor(system_db):
    c, h = _admin_client(system_db)
    with system_conn() as conn:
        for codigo, nome in (("asaas", "Asaas"), ("mercadopago", "Mercado Pago"), ("efipay", "EfiPay"), ("sicoob", "Sicoob")):
            conn.execute(
                "INSERT INTO payment_provider (codigo, nome) VALUES (%s, %s) ON CONFLICT (codigo) DO NOTHING",
                (codigo, nome),
            )
        conn.commit()
    r = c.get("/api/payment-providers", headers=h)
    assert r.status_code == 200
    body = r.get_json()
    codigos = [p["codigo"] for p in body["providers"]]
    assert "asaas" in codigos and "mercadopago" in codigos

    _config_asaas(system_db, "pix")
    r2 = c.get("/api/payment-providers", headers=h)
    configs = r2.get_json()["configs"]
    assert any(x["operacao"] == "pix" and x["provider_codigo"] == "asaas" for x in configs)


def test_emitir_boleto_asaas(system_db):
    c, h = _admin_client(system_db)
    _config_asaas(system_db, "boleto")
    conta_id = _conta(system_db)
    resp_mock = {
        "id": "pay_123",
        "bankSlip": {"line": "00190500954014481606906809350314337370000000100", "barcode": "0019050095"},
        "bankSlipUrl": "https://sandbox.asaas.com/pay/pay_123",
        "nossoNumero": "00000001",
    }
    with patch("requests.post") as mpost, patch("requests.get") as mget:
        # GET /customers -> nÃ£o encontrou (cria novo)
        mget.return_value = type("R", (), {"ok": False, "status_code": 404, "text": "", "json": lambda: {}})()
        # POST /customers -> id; POST /payments -> boleto
        mpost.side_effect = [
            type("R", (), {"ok": True, "json": lambda *args: {"id": "cus_1"}})(),
            type("R", (), {"ok": True, "json": lambda *args: resp_mock})(),
        ]
        r = c.post(f"/api/financeiro/receber/{conta_id}/cobranca", headers=h, json={"operacao": "boleto"})
        assert r.status_code == 200, r.get_json()
        body = r.get_json()
        assert body["payment_id"] == "pay_123"
        assert body["operacao"] == "boleto"
    with system_conn() as conn:
        row = conn.execute("SELECT * FROM contas_receber WHERE id=%s", (conta_id,)).fetchone()
    assert row["payment_id"] == "pay_123"
    assert row["status_cobranca"] == "pendente"


def test_webhook_baixa_automatica_idempotente(system_db):
    c, h = _admin_client(system_db)
    _config_asaas(system_db, "pix")
    conta_id = _conta(system_db)
    resp_pix = {"id": "pay_999", "pixQrCode": "0002012658...", "pixQrCodeBase64": "iVBORw0KGgo=", "invoiceUrl": "https://x"}
    with patch("requests.post") as mpost, patch("requests.get") as mget:
        mget.return_value = type("R", (), {"ok": False, "status_code": 404, "text": "", "json": lambda: {}})()
        mpost.side_effect = [
            type("R", (), {"ok": True, "json": lambda *args: {"id": "cus_1"}})(),
            type("R", (), {"ok": True, "json": lambda *args: resp_pix})(),
        ]
        c.post(f"/api/financeiro/receber/{conta_id}/cobranca", headers=h, json={"operacao": "pix"})

    payload = {
        "event": "PAYMENT_RECEIVED",
        "payment": {"id": "pay_999", "status": "RECEIVED", "value": 500.0},
    }
    r = c.post("/api/webhooks/payments/asaas", json=payload)
    assert r.status_code == 200
    assert r.get_json()["ok"] is True
    with system_conn() as conn:
        row = conn.execute("SELECT * FROM contas_receber WHERE id=%s", (conta_id,)).fetchone()
    assert row["status"] == "pago"
    assert row["saldo"] == 0
    assert row["status_cobranca"] == "pago"

    # idempotente: segundo webhook nÃ£o altera
    r2 = c.post("/api/webhooks/payments/asaas", json=payload)
    assert r2.get_json()["duplicado"] is True


def test_receber_manual_com_forma(system_db):
    c, h = _admin_client(system_db)
    conta_id = _conta(system_db)
    r = c.post(f"/api/financeiro/receber/{conta_id}/receber", headers=h,
               json={"valor": 500.0, "forma_pagamento": "cheque"})
    assert r.status_code == 200, r.get_json()
    assert r.get_json()["status"] == "pago"
    with system_conn() as conn:
        row = conn.execute("SELECT * FROM contas_receber WHERE id=%s", (conta_id,)).fetchone()
    assert row["status"] == "pago"


def test_comprovante_deposito(system_db):
    c, h = _admin_client(system_db)
    conta_id = _conta(system_db)
    data = {
        "file": (io.BytesIO(b"fakepdf"), "comprovante.pdf"),
        "tipo": "ted",
"descricao": "Depósito TED",
    }
    r = c.post(f"/api/financeiro/receber/{conta_id}/comprovante", headers=h,
               data=data, content_type="multipart/form-data")
    assert r.status_code == 200, r.get_json()
    with system_conn() as conn:
        comp = conn.execute("SELECT * FROM conta_comprovante WHERE conta_id=%s", (conta_id,)).fetchone()
    assert comp is not None
    assert comp["tipo"] == "ted"


def _config(system_db, codigo, operacao, **extra):
    """Cria config de um provedor (fase 2) com credenciais."""
    from catalog_server.payments.repo import payment_provider_repo

    with system_conn() as conn:
        conn.execute(
            "INSERT INTO payment_provider (codigo, nome) VALUES (%s, %s) ON CONFLICT (codigo) DO NOTHING",
            (codigo, codigo.capitalize()),
        )
        pid = int(conn.execute(
            "SELECT id FROM payment_provider WHERE codigo=%s", (codigo,)
        ).fetchone()["id"])
        conn.commit()
    dados = {"provider_id": pid, "operacao": operacao, "ambiente": "sandbox",
             "prioridade": 1, "ativo": 1}
    dados.update(extra)
    payment_provider_repo.upsert_config(dados)


def _mock_resp(payload):
    return type("R", (), {"ok": True, "status_code": 200, "json": lambda *a: payload, "text": ""})


def test_emitir_boleto_efipay(system_db):
    """EfiPay (fase 2): OAuth2 + certificado; boleto via /v1/charges."""
    c, h = _admin_client(system_db)
    _config(system_db, "efipay", "boleto", client_id="efi_id", client_secret="efi_secret", certificado="/tmp/cert.pem")
    conta_id = _conta(system_db)
    charge_resp = {
        "id": "ch_123",
        "payment": {"banking_billet": {
            "linha_digitavel": "00190.50095 40144.816906 80690.350314 3 73370000000100",
            "barcode": "00190500954014481690680690350314337370000000100",
            "nosso_numero": "00000001",
            "link": "https://efipay.com.br/boleto/xxx",
        }},
    }
    with patch("requests.post") as mpost:
        mpost.side_effect = [
            _mock_resp({"access_token": "tok_efi"}),
            _mock_resp(charge_resp),
        ]
        r = c.post(f"/api/financeiro/receber/{conta_id}/cobranca", headers=h, json={"operacao": "boleto"})
        assert r.status_code == 200, r.get_json()
        body = r.get_json()
        assert body["payment_id"] == "ch_123"
        assert body["provider"] == "efipay"
        assert body["linha_digitavel"]


def test_emitir_pix_sicoob_webhook(system_db):
    """Sicoob (fase 2): sandbox token direto; PIX cob + webhook baixa."""
    c, h = _admin_client(system_db)
    _config(system_db, "sicoob", "pix", client_id="sicoob_id", access_token="bearer_teste", chave_pix="chave@teste.com")
    conta_id = _conta(system_db)
    cob_resp = {
        "txid": "tx123",
        "pixCopiaECola": "00020126580014br.gov.bcb.pix0136...",
        "loc": {"location": "https://sicoob/pix/tx123"},
    }
    with patch("requests.post") as mpost:
        mpost.return_value = _mock_resp(cob_resp)
        r = c.post(f"/api/financeiro/receber/{conta_id}/cobranca", headers=h, json={"operacao": "pix"})
        assert r.status_code == 200, r.get_json()
        body = r.get_json()
        assert body["payment_id"] == "tx123"
        assert body["provider"] == "sicoob"
        assert body["payload_pix"]

    # webhook Sicoob PIX baixa automaticamente
    payload = {"pix": [{"txid": "tx123", "valor": "500.00", "status": "CONCLUIDA"}]}
    rw = c.post("/api/webhooks/payments/sicoob", json=payload)
    assert rw.status_code == 200
    assert rw.get_json()["ok"] is True
    with system_conn() as conn:
        row = conn.execute("SELECT * FROM contas_receber WHERE id=%s", (conta_id,)).fetchone()
    assert row["status"] == "pago"
