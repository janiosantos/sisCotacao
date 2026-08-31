"""Outbox transacional (P5) — migração 0101."""
from __future__ import annotations

from unittest.mock import patch

from catalog_server.db import system_conn
from catalog_server.services import outbox


def test_outbox_enfileirar_e_processar_ok(system_db):
    oid = outbox.enfileirar("webhook.rechecagem", {"payment_id": "pay_outbox_1"},
                            chave_idempotencia="wh:pay_outbox_1")
    assert oid > 0
    assert outbox.pendentes_contagem() >= 1

    # idempotência: mesma chave não duplica
    oid2 = outbox.enfileirar("webhook.rechecagem", {"payment_id": "pay_outbox_1"},
                            chave_idempotencia="wh:pay_outbox_1")
    assert oid2 == oid
    assert outbox.pendentes_contagem() >= 1

    from catalog_server.jobs import tasks

    with patch("catalog_server.jobs.tasks.processar_item") as m:
        res = tasks.rodar_outbox(limite=10)
    assert res["processados"] >= 1
    assert res["ok"] >= 1
    assert m.called


def test_outbox_erro_vira_morta_apos_max_tentativas(system_db):
    from catalog_server.jobs import tasks

    oid = outbox.enfileirar("topico.sem_handler", {"x": 1})
    # backoff agenda proxima_tentativa no futuro; força a re-tentativa a cada loop
    for _ in range(outbox.MAX_TENTATIVAS + 1):
        with system_conn() as conn:
            conn.execute(
                "UPDATE outbox SET proxima_tentativa=NOW() - interval '1 hour' WHERE id=%s", (oid,)
            )
            conn.commit()
        tasks.rodar_outbox(limite=50)
    with system_conn() as conn:
        row = conn.execute("SELECT status, tentativas FROM outbox WHERE id=%s", (oid,)).fetchone()
    assert row["status"] == "morta"
    assert row["tentativas"] >= outbox.MAX_TENTATIVAS


def test_outbox_webhook_rechecagem_handler(system_db):
    from catalog_server.jobs import tasks

    with patch("catalog_server.jobs.tasks.webhook_log.rechecagem",
               return_value={"verificadas": 1, "pagas": 1, "ja_pagas": 0, "erros": [], "detalhes": []}) as m:
        res = tasks.processar_item({"topico": "webhook.rechecagem",
                                    "payload": '{"payment_id": "pay_x"}'})
    m.assert_called_once_with(payment_id="pay_x", limite=1)


def test_outbox_rejeita_payload_invalido(system_db):
    from catalog_server.jobs import tasks

    with patch("catalog_server.jobs.tasks.webhook_log.rechecagem") as m:
        try:
            tasks.processar_item({"topico": "webhook.rechecagem", "payload": "[1,2]"})
        except ValueError as exc:
            assert "objeto JSON" in str(exc)
        else:
            raise AssertionError("payload não-objeto deveria falhar")
        m.assert_not_called()


def test_outbox_rechecagem_com_erro_falha_para_retry(system_db):
    from catalog_server.jobs import tasks

    with patch(
        "catalog_server.jobs.tasks.webhook_log.rechecagem",
        return_value={"erros": ["provider indisponível"]},
    ):
        try:
            tasks.processar_item({"topico": "webhook.rechecagem", "payload": '{"payment_id":"p"}'})
        except RuntimeError as exc:
            assert "provider indisponível" in str(exc)
        else:
            raise AssertionError("erro de rechecagem deveria falhar para retry")


def test_webhook_503_enfileira_outbox(system_db):
    from catalog_server.app_factory import create_app

    # provider sem config -> webhook 503 + outbox enfileirado
    c = create_app().test_client()
    payload = {"event": "PAYMENT_RECEIVED", "payment": {"id": "pay_sem_config"}}
    r = c.post("/api/webhooks/payments/asaas", json=payload)
    assert r.status_code == 503
    with system_conn() as conn:
        row = conn.execute(
            "SELECT topico, status FROM outbox"
            " WHERE idempotencia_key='webhook:asaas:pay_sem_config'"
        ).fetchone()
    assert row is not None
    assert row["topico"] == "webhook.rechecagem"
    assert row["status"] in ("pendente", "ok")
