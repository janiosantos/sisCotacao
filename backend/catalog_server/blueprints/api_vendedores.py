from __future__ import annotations

from flask import Blueprint, jsonify, request

from catalog_server.repositories import vendedor_repo

api_vendedores_bp = Blueprint("api_vendedores", __name__)


@api_vendedores_bp.get("/api/vendedores")
def listar():
    somente_ativos = request.args.get("somente_ativos", "").lower() in ("1", "true")
    return jsonify(vendedor_repo.list(somente_ativos=somente_ativos))


@api_vendedores_bp.get("/api/vendedores/<int:vendedor_id>")
def detalhar(vendedor_id: int):
    vendedor = vendedor_repo.get(vendedor_id)
    if not vendedor:
        return jsonify({"error": "Vendedor não encontrado"}), 404
    return jsonify(vendedor)


@api_vendedores_bp.post("/api/vendedores")
def criar():
    data = request.get_json(silent=True) or {}
    nome = (data.get("nome") or "").strip()
    if not nome:
        return jsonify({"error": "Informe o nome do vendedor"}), 400
    vendedor_id = vendedor_repo.create(nome, float(data.get("comissao_pct") or 0))
    return jsonify({"id": vendedor_id}), 201


@api_vendedores_bp.put("/api/vendedores/<int:vendedor_id>")
def atualizar(vendedor_id: int):
    data = request.get_json(silent=True) or {}
    if not (data.get("nome") or "").strip():
        return jsonify({"error": "Informe o nome do vendedor"}), 400
    ok = vendedor_repo.update(vendedor_id, data.get("nome"), float(data.get("comissao_pct") or 0))
    if not ok:
        return jsonify({"error": "Vendedor não encontrado"}), 404
    return jsonify({"ok": True})


@api_vendedores_bp.patch("/api/vendedores/<int:vendedor_id>/ativo")
def alternar_ativo(vendedor_id: int):
    ativo = request.args.get("ativo", "").lower() in ("1", "true")
    ok = vendedor_repo.set_ativo(vendedor_id, ativo)
    if not ok:
        return jsonify({"error": "Vendedor não encontrado"}), 404
    return jsonify({"ok": True})