from __future__ import annotations

from flask import Blueprint, jsonify, request

from catalog_server.repositories import condicao_repo, supplier_repo
from catalog_server.repositories.suppliers import CATEGORIAS

api_suppliers_bp = Blueprint("api_suppliers", __name__)


@api_suppliers_bp.get("/api/fornecedores")
def listar():
    somente_ativos = request.args.get("somente_ativos", "").lower() in ("1", "true")
    categoria = request.args.get("categoria") or None
    q = request.args.get("q") or None
    return jsonify(supplier_repo.list(
        somente_ativos=somente_ativos, categoria=categoria, termo=q,
    ))


@api_suppliers_bp.get("/api/fornecedores/<int:fornecedor_id>")
def detalhar(fornecedor_id: int):
    f = supplier_repo.get(fornecedor_id)
    if not f:
        return jsonify({"error": "Fornecedor não encontrado"}), 404
    return jsonify(f)


@api_suppliers_bp.get("/api/fornecedores/contexto")
def contexto():
    """Dados auxiliares para o formulário de fornecedor (categorias, condições)."""
    return jsonify({
        "categorias": [{"valor": c, "label": c.capitalize()} for c in CATEGORIAS],
        "condicoes_pagamento": condicao_repo.list(),
    })


@api_suppliers_bp.post("/api/fornecedores")
def criar():
    data = request.get_json(silent=True) or {}
    nome = (data.get("nome") or "").strip()
    if not nome:
        return jsonify({"error": "Informe o nome do fornecedor"}), 400
    fornecedor_id = supplier_repo.create(data)
    return jsonify({"id": fornecedor_id})


@api_suppliers_bp.put("/api/fornecedores/<int:fornecedor_id>")
def atualizar(fornecedor_id: int):
    data = request.get_json(silent=True) or {}
    nome = (data.get("nome") or "").strip()
    if not nome:
        return jsonify({"error": "Informe o nome do fornecedor"}), 400
    ok = supplier_repo.update(fornecedor_id, data)
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


# ── Contatos ───────────────────────────────────────────────

@api_suppliers_bp.get("/api/fornecedores/<int:fornecedor_id>/contatos")
def listar_contatos(fornecedor_id: int):
    return jsonify(supplier_repo.listar_contatos(fornecedor_id))


@api_suppliers_bp.post("/api/fornecedores/<int:fornecedor_id>/contatos")
def criar_contato(fornecedor_id: int):
    data = request.get_json(silent=True) or {}
    if not (data.get("nome") or "").strip():
        return jsonify({"error": "nome do contato obrigatório"}), 400
    ct_id = supplier_repo.criar_contato(fornecedor_id, data)
    return jsonify({"id": ct_id}), 201


@api_suppliers_bp.delete("/api/fornecedores/contatos/<int:contato_id>")
def excluir_contato(contato_id: int):
    if not supplier_repo.excluir_contato(contato_id):
        return jsonify({"error": "Contato não encontrado"}), 404
    return jsonify({"ok": True})