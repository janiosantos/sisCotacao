"""Endpoints de status/versionamento do sistema (controle de atualização)."""
from __future__ import annotations

from flask import Blueprint, jsonify, request

from catalog_server.versioning import (
    apply_updates,
    listar_log,
    listar_manifestos_pendentes,
    system_status,
)

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
    usuario = request.usuario.get("login") if getattr(request, "usuario", None) else None
    try:
        result = apply_updates(riscos=riscos, origem="painel", usuario=usuario)
    except Exception as exc:  # noqa: BLE001 - reporta erro ao operador
        return jsonify({"ok": False, "error": str(exc)}), 500
    result["ok"] = True
    result["nivel"] = nivel
    return jsonify(result), 200


@api_sistema_bp.get("/api/sistema/updates/log")
def updates_log():
    """Histórico de atualizações aplicadas (deploy ou painel)."""
    try:
        return jsonify({"log": listar_log(limite=50)}), 200
    except Exception as exc:  # noqa: BLE001 - expõe erro de infra ao operador
        return jsonify({"error": str(exc)}), 500


@api_sistema_bp.get("/api/sistema/releases/pendentes")
def releases_pendentes():
    """Manifestos de release ainda não publicados (rascunhos acumulados em dev)."""
    try:
        return jsonify({"pendentes": listar_manifestos_pendentes()}), 200
    except Exception as exc:  # noqa: BLE001 - expõe erro de infra ao operador
        return jsonify({"error": str(exc)}), 500
