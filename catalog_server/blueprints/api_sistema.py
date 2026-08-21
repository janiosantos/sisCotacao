"""Endpoints de status/versionamento do sistema (controle de atualização)."""
from __future__ import annotations

from flask import Blueprint, jsonify, request

from catalog_server.versioning import apply_updates, system_status

api_sistema_bp = Blueprint("api_sistema", __name__)


@api_sistema_bp.get("/api/sistema/status")
def status():
    """Estado do sistema: versão do app, versão do schema e pendências por risco.

    Somente-leitura — não aplica migrações. Use para o painel de "Atualizações".
    """
    try:
        return jsonify(system_status()), 200
    except Exception as exc:  # noqa: BLE001 - expõe erro de infra ao operador
        return jsonify({"error": str(exc)}), 500


# Nível escolhido no painel -> riscos aplicados. Críticas sempre entram (não se
# pode pular a ordem de migração); "melhoria" engloba tudo.
_RISCO_MAP = {
    "critica": ["critica"],
    "rotina": ["critica", "rotina"],
    "melhoria": ["critica", "rotina", "melhoria"],
    "todos": None,
}


@api_sistema_bp.post("/api/sistema/updates/apply")
def apply_pending():
    """Aplica atualizações pendentes por nível de risco (on-demand)."""
    body = request.get_json(silent=True) or {}
    nivel = body.get("risco", "todos")
    riscos = _RISCO_MAP.get(nivel, None)
    try:
        result = apply_updates(riscos=riscos)
    except Exception as exc:  # noqa: BLE001 - reporta erro ao operador
        return jsonify({"ok": False, "error": str(exc)}), 500
    result["ok"] = True
    result["nivel"] = nivel
    return jsonify(result), 200
