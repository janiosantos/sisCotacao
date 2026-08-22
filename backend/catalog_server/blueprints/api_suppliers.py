from __future__ import annotations

from flask import Blueprint, jsonify, request

from catalog_server.repositories import supplier_repo

api_suppliers_bp = Blueprint("api_suppliers", __name__)


@api_suppliers_bp.get("/api/fornecedores")
def listar():
    somente_ativos = request.args.get("somente_ativos", "").lower() in ("1", "true")
    return jsonify(supplier_repo.list(somente_ativos=somente_ativos))


@api_suppliers_bp.post("/api/fornecedores")
def criar():
    data = request.get_json(silent=True) or {}
    nome = (data.get("nome") or "").strip()
    if not nome:
        return jsonify({"error": "Informe o nome do fornecedor"}), 400
    fornecedor_id = supplier_repo.create(
        nome,
        (data.get("whatsapp") or "").strip(),
        (data.get("email") or "").strip(),
        (data.get("observacoes") or "").strip(),
        (data.get("razao_social") or "").strip(),
        (data.get("cnpj_cpf") or "").strip(),
        (data.get("representante") or "").strip(),
    )
    return jsonify({"id": fornecedor_id})


@api_suppliers_bp.put("/api/fornecedores/<int:fornecedor_id>")
def atualizar(fornecedor_id: int):
    data = request.get_json(silent=True) or {}
    nome = (data.get("nome") or "").strip()
    if not nome:
        return jsonify({"error": "Informe o nome do fornecedor"}), 400
    ok = supplier_repo.update(
        fornecedor_id,
        nome,
        (data.get("whatsapp") or "").strip(),
        (data.get("email") or "").strip(),
        (data.get("observacoes") or "").strip(),
        (data.get("razao_social") or "").strip(),
        (data.get("cnpj_cpf") or "").strip(),
        (data.get("representante") or "").strip(),
    )
    if not ok:
        return jsonify({"error": "Fornecedor não encontrado"}), 404
    return jsonify({"ok": True})


@api_suppliers_bp.patch("/api/fornecedores/<int:fornecedor_id>/ativo")
def alternar_ativo(fornecedor_id: int):
    ativo = request.args.get("ativo", "").lower() in ("1", "true")
    ok = supplier_repo.set_ativo(fornecedor_id, ativo)
    if not ok:
        return jsonify({"error": "Fornecedor não encontrado"}), 404
    return jsonify({"ok": True})
