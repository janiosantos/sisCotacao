"""Tarefas de segundo plano (worker RQ)."""
from __future__ import annotations

from catalog_server.services import webhook_log


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