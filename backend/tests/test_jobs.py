"""Jobs assíncronos (P5) — tarefa de rechecagem."""
from __future__ import annotations

from unittest.mock import patch


def test_task_rechecagem(system_db):
    from catalog_server.jobs import tasks

    res_mock = {
        "verificadas": 2, "pagas": 1, "ja_pagas": 0,
        "erros": [], "detalhes": [{"conta_id": 1, "payment_id": "x", "valor": 5.0}],
    }
    with patch("catalog_server.jobs.tasks.webhook_log.rechecagem", return_value=res_mock) as m, \
         patch("catalog_server.jobs.tasks.webhook_log.registrar") as r:
        res = tasks.rechecagem(provider="asaas")
    assert res["pagas"] == 1
    m.assert_called_once_with(provider="asaas", limite=100)
    r.assert_called_once()


def test_worker_e_scheduler_importam():
    import catalog_server.jobs.scheduler  # noqa: F401
    import catalog_server.jobs.worker  # noqa: F401