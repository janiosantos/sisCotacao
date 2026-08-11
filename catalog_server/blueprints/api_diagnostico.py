from __future__ import annotations

from flask import Blueprint, jsonify, request

from catalog_server.repositories import diagnostico_repo

api_diagnostico_bp = Blueprint("api_diagnostico", __name__)


@api_diagnostico_bp.get("/api/catalogo/diagnostico-variacoes/resumo")
def resumo():
    return jsonify(diagnostico_repo.resumo())


@api_diagnostico_bp.get("/api/catalogo/diagnostico-variacoes")
def listar():
    revisado = request.args.get("revisado")
    return jsonify(diagnostico_repo.list(
        classificacao=request.args.get("classificacao") or None,
        revisado=None if revisado is None else revisado.lower() in ("1", "true"),
        termo=request.args.get("q", "").strip() or None,
        limit=request.args.get("limit", 100, type=int),
    ))


@api_diagnostico_bp.get("/api/catalogo/diagnostico-variacoes/<int:produto_id>")
def detalhes(produto_id: int):
    return jsonify(diagnostico_repo.detalhes(produto_id))


@api_diagnostico_bp.patch("/api/catalogo/diagnostico-variacoes/<int:produto_id>/revisado")
def marcar_revisado(produto_id: int):
    data = request.get_json(silent=True) or {}
    if not diagnostico_repo.marcar_revisado(produto_id, bool(data.get("revisado", True))):
        return jsonify({"error": "Diagnóstico não encontrado"}), 404
    return jsonify({"ok": True})


@api_diagnostico_bp.post("/api/catalogo/diagnostico-variacoes/<int:produto_id>/consolidar")
def consolidar(produto_id: int):
    data = request.get_json(silent=True) or {}
    principal_id = data.get("principal_id")
    if not principal_id:
        return jsonify({"error": "principal_id obrigatório"}), 400
    try:
        return jsonify(diagnostico_repo.consolidar_ofertas(produto_id, int(principal_id)))
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
