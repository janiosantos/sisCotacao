"""API da matriz de regras fiscais (módulo Fiscal).

CRUD de regras, versionamento com vigência e auditoria. A resolução em si
fica no serviço `fiscal_regras.buscar_regra` (consumida pelo motor).
"""
from __future__ import annotations

from flask import Blueprint, jsonify, request

from catalog_server.blueprints.api_usuarios import usuario_id_requisicao
from catalog_server.repositories import fiscal_regra_repo, fiscal_regra_versao_repo
from catalog_server.services import fiscal_regras

api_fiscal_regras_bp = Blueprint("api_fiscal_regras", __name__)


def _usuario() -> int | None:
    return usuario_id_requisicao()


@api_fiscal_regras_bp.get("/api/fiscal/regras")
def listar_regras():
    return jsonify(fiscal_regra_repo.list({
        "regime": request.args.get("regime"),
        "uf_destino": request.args.get("uf_destino"),
        "tipo_cliente": request.args.get("tipo_cliente"),
        "contribuinte": request.args.get("contribuinte"),
        "finalidade": request.args.get("finalidade"),
        "modelo_documento": request.args.get("modelo_documento"),
        "ncm": request.args.get("ncm"),
        "somente_ativos": request.args.get("somente_ativos", "").lower() in ("1", "true"),
    }))


@api_fiscal_regras_bp.get("/api/fiscal/regras/<int:regra_id>")
def detalhar_regra(regra_id: int):
    r = fiscal_regra_repo.get(regra_id)
    if not r:
        return jsonify({"error": "Regra não encontrada"}), 404
    r["versoes"] = fiscal_regra_versao_repo.list(regra_id)
    return jsonify(r)


@api_fiscal_regras_bp.post("/api/fiscal/regras")
def criar_regra():
    data = request.get_json(silent=True) or {}
    if not (data.get("nome") or "").strip():
        return jsonify({"error": "Informe o nome da regra"}), 400
    rid = fiscal_regra_repo.create(data, usuario_id=_usuario(), motivo=data.get("motivo") or "")
    return jsonify({"id": rid}), 201


@api_fiscal_regras_bp.put("/api/fiscal/regras/<int:regra_id>")
def atualizar_regra(regra_id: int):
    data = request.get_json(silent=True) or {}
    if not fiscal_regra_repo.update(regra_id, data, usuario_id=_usuario(), motivo=data.get("motivo") or ""):
        return jsonify({"error": "Regra não encontrada"}), 404
    return jsonify({"ok": True})


@api_fiscal_regras_bp.patch("/api/fiscal/regras/<int:regra_id>/ativo")
def alternar_ativo_regra(regra_id: int):
    ativo = request.args.get("ativo", "").lower() in ("1", "true")
    motivo = request.args.get("motivo") or ""
    if not fiscal_regra_repo.set_ativo(regra_id, ativo, usuario_id=_usuario(), motivo=motivo):
        return jsonify({"error": "Regra não encontrada"}), 404
    return jsonify({"ok": True})


# ─── Versões ───────────────────────────────────────────────

@api_fiscal_regras_bp.post("/api/fiscal/regras/<int:regra_id>/versoes")
def criar_versao(regra_id: int):
    data = request.get_json(silent=True) or {}
    versao = (data.get("versao") or "").strip()
    inicio = (data.get("data_inicio") or "").strip()
    fonte = (data.get("fonte") or "").strip()
    if not versao or not inicio:
        return jsonify({"error": "versao e data_inicio obrigatórios"}), 400
    vid = fiscal_regra_versao_repo.create(
        regra_id, versao, fonte, inicio, data.get("data_fim"), data.get("parametros"),
    )
    return jsonify({"id": vid}), 201


@api_fiscal_regras_bp.patch("/api/fiscal/regras/versoes/<int:versao_id>")
def alterar_status_versao(versao_id: int):
    data = request.get_json(silent=True) or {}
    if not fiscal_regra_versao_repo.set_status(
        versao_id, data.get("status", ""), usuario_id=_usuario(), motivo=data.get("motivo") or ""
    ):
        return jsonify({"error": "Versão não encontrada ou status inválido"}), 404
    return jsonify({"ok": True})


# ─── Auditoria e resolução ─────────────────────────────────

@api_fiscal_regras_bp.get("/api/fiscal/regras/auditoria")
def listar_auditoria():
    regra_id = request.args.get("regra_id", type=int)
    return jsonify(fiscal_regra_repo.list_auditoria(regra_id=regra_id))


@api_fiscal_regras_bp.post("/api/fiscal/regras/resolver")
def resolver_regra():
    """Resolve a regra vigente para um contexto+data (sem calcular tributos)."""
    data = request.get_json(silent=True) or {}
    regra = fiscal_regras.buscar_regra(data.get("contexto") or {}, data.get("data"))
    if regra is None:
        return jsonify({"status": "FISCAL_RULE_NOT_FOUND"}), 404
    return jsonify({"status": "ok", "regra": regra})
