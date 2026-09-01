"""Endpoints de status/versionamento do sistema (controle de atualização)."""
from __future__ import annotations

from pathlib import Path

from flask import Blueprint, jsonify, request, send_file

from catalog_server import flags
from catalog_server.versioning import (
    apply_updates,
    listar_log,
    listar_manifestos_pendentes,
    system_status,
)

api_sistema_bp = Blueprint("api_sistema", __name__)


@api_sistema_bp.get("/api/openapi.json")
def openapi_spec():
    """Contrato da API (fase 1) — fonte única em backend/openapi.json."""
    aqui = Path(__file__).resolve()
    for cand in (
        aqui.parent.parent.parent / "openapi.json",  # container: /app/openapi.json
        aqui.parent.parent / "openapi.json",         # repo local: backend/openapi.json
    ):
        if cand.is_file():
            return send_file(cand, mimetype="application/json")
    return jsonify({"error": "openapi.json não encontrado"}), 500


@api_sistema_bp.get("/api/sistema/status")
def status():
    """Estado do sistema: versão do app, versão do schema e pendências por risco.

    Somente-leitura — não aplica migrações. Use para o painel de "Atualizações".
    """
    try:
        return jsonify(system_status()), 200
    except Exception as exc:  # noqa: BLE001 - expõe erro de infra ao operador
        return jsonify({"error": str(exc)}), 500


@api_sistema_bp.get("/api/sistema/readiness")
def readiness():
    """Readiness (ADM-005): banco ok, sem migrações pendentes, outbox saudável."""
    from catalog_server.services import outbox

    try:
        with system_conn() as conn:
            conn.execute("SELECT 1")
        banco = "ok"
    except Exception:  # noqa: BLE001
        banco = "erro"
    status_info = system_status()
    pendentes = len(status_info.get("pending", []) or [])
    outbox_mortas = 0
    try:
        outbox_mortas = len([e for e in outbox.listar(status="morta", limite=100)])
    except Exception:  # noqa: BLE001
        pass
    pronto = banco == "ok" and pendentes == 0
    return jsonify({
        "ready": pronto,
        "checks": {
            "banco": banco,
            "migrations_pendentes": pendentes,
            "outbox_morta": outbox_mortas,
        },
        "schema": status_info.get("schema_version"),
    }), (200 if pronto else 503)


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


@api_sistema_bp.get("/api/flags")
def listar_flags():
    """Feature flags registradas com estado atual."""
    return jsonify({"flags": flags.listar()}), 200


@api_sistema_bp.put("/api/flags/<nome>")
def definir_flag(nome: str):
    """Liga/desliga uma feature flag registrada (rollback comportamental)."""
    body = request.get_json(silent=True) or {}
    try:
        flags.definir(nome, bool(body.get("ativo")))
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 404
    except Exception as exc:  # noqa: BLE001 - expõe erro de infra ao operador
        return jsonify({"error": str(exc)}), 500
    return jsonify({"ok": True, "nome": nome, "ativo": bool(body.get("ativo"))}), 200
