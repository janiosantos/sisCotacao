"""Tarefas de segundo plano (worker RQ)."""
from __future__ import annotations

import json

from catalog_server.services import outbox, webhook_log


def rechecagem(provider: str = "", limite: int = 100) -> dict:
    """Rechecagem em lotes das cobranças pendentes (consulta o provedor e baixa as pagas).

    Executada periodicamente pelo scheduler. Registra o resultado no log de webhooks
    (evento='rechecagem') para auditoria.
    """
    resultado = webhook_log.rechecagem(provider=provider, limite=limite)
    webhook_log.registrar(
        provider or "geral",
        "processado" if not resultado["erros"] else "erro",
        evento="rechecagem_agendada",
        erro=f"verificadas={resultado['verificadas']} pagas={resultado['pagas']} erros={len(resultado['erros'])}",
        payment_id="",
    )
    return resultado


# ─── Outbox transacional ──────────────────────────────────────


def _handler_rechecagem_conta(payload: dict) -> dict:
    """Recheca uma conta específica (webhook falhou / provider não configurado)."""
    payment_id = str(payload.get("payment_id") or "")
    if not payment_id:
        raise ValueError("Outbox: payment_id obrigatório para rechecagem")
    resultado = webhook_log.rechecagem(payment_id=payment_id, limite=1)
    if resultado.get("erros"):
        raise RuntimeError("; ".join(str(e) for e in resultado["erros"]))
    return resultado


_HANDLERS = {
    "webhook.rechecagem": _handler_rechecagem_conta,
}


def processar_item(item: dict) -> dict:
    topico = item["topico"]
    try:
        payload = json.loads(item["payload"] or "{}")
    except (ValueError, TypeError):
        raise ValueError("Outbox: payload JSON inválido") from None
    if not isinstance(payload, dict):
        raise ValueError("Outbox: payload deve ser um objeto JSON")
    handler = _HANDLERS.get(topico)
    if not handler:
        raise ValueError(f"Outbox: tópico sem handler: {topico}")
    resultado = handler(payload) or {}
    if resultado.get("erros"):
        raise RuntimeError("; ".join(str(e) for e in resultado["erros"]))
    return resultado


def rodar_outbox(limite: int = 50) -> dict:
    """Processa as linhas do outbox prontas (worker RQ). Retry/backoff e dead-letter."""
    itens = outbox.prontas(limite)
    processados = ok = erros = 0
    for item in itens:
        try:
            processar_item(item)
            outbox.marcar_ok(item["id"])
            ok += 1
        except Exception as exc:
            outbox.marcar_erro(item["id"], str(exc))
            erros += 1
        processados += 1
    return {"processados": processados, "ok": ok, "erros": erros, "pendentes": outbox.pendentes_contagem()}
