"""Endpoints de status/versionamento do sistema (controle de atualização)."""
from __future__ import annotations

from flask import Blueprint, jsonify

from catalog_server.versioning import system_status

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
