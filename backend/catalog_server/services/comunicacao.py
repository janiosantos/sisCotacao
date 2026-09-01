"""Comunicação externa (INT-006): e-mail/WhatsApp de cotação/pedido via outbox
(retry/backoff/dead-letter). Envio externo não bloqueia a compra; retry não
duplica; falha tem ação (dead-letter).
"""

from __future__ import annotations

from catalog_server.db import system_conn
from catalog_server.services import outbox


def agendar(tipo: str, destinatario: str, template: str, dados: dict,
            chave_idempotencia: str = "", origem: str | None = None) -> int:
    """Agenda envio (e-mail/whatsapp) no outbox — assíncrono, não bloqueia o fluxo."""
    tipo = (tipo or "").strip().lower()
    if tipo not in ("email", "whatsapp"):
        raise ValueError("tipo inválido (email|whatsapp)")
    if not destinatario:
        raise ValueError("destinatario é obrigatório")
    payload = {"tipo": tipo, "destinatario": destinatario, "template": template,
               "dados": dados, "origem": origem}
    return outbox.enfileirar("comunicacao", payload, chave_idempotencia or "")


def listar_envios(status: str = "", limite: int = 50) -> list[dict]:
    envios = outbox.listar(status=status, limite=limite)
    out = []
    with system_conn() as conn:
        for e in envios:
            if e.get("topico") == "comunicacao":
                import json
                try:
                    payload = json.loads(e["payload"])
                except (TypeError, ValueError):
                    payload = {}
                out.append({**e, "tipo": payload.get("tipo"), "destinatario": _mascarar(payload.get("destinatario")),
                            "template": payload.get("template"), "origem": payload.get("origem")})
    return out


def _mascarar(destinatario):
    if not destinatario:
        return None
    s = str(destinatario)
    if "@" in s:
        return s[:2] + "***@" + s.split("@")[1]
    if len(s) >= 8:
        return s[:3] + "****" + s[-2:]
    return s