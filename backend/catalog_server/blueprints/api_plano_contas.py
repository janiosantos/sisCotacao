from __future__ import annotations

from flask import Blueprint, jsonify, request

from catalog_server.repositories import plano_conta_repo

api_plano_contas_bp = Blueprint("api_plano_contas", __name__)


@api_plano_contas_bp.get("/api/plano-contas")
def listar():
    tipo = request.args.get("tipo") or None
    somente_ativos = request.args.get("somente_ativos", "").lower() in ("1", "true")
    return jsonify(plano_conta_repo.list(tipo=tipo, somente_ativos=somente_ativos))


@api_plano_contas_bp.get("/api/plano-contas/<int:conta_id>")
def detalhar(conta_id: int):
    conta = plano_conta_repo.get(conta_id)
    if not conta:
        return jsonify({"error": "Conta não encontrada"}), 404
    return jsonify(conta)


@api_plano_contas_bp.post("/api/plano-contas")
def criar():
    data = request.get_json(silent=True) or {}
    codigo = (data.get("codigo") or "").strip()
    nome = (data.get("nome") or "").strip()
    tipo = data.get("tipo") or "receita"
    if not codigo or not nome:
        return jsonify({"error": "Informe código e nome da conta"}), 400
    if tipo not in ("receita", "despesa"):
        return jsonify({"error": "Tipo deve ser receita ou despesa"}), 400
    conta_id = plano_conta_repo.create(codigo, nome, tipo, data.get("pai_id") or None)
    return jsonify({"id": conta_id}), 201


@api_plano_contas_bp.put("/api/plano-contas/<int:conta_id>")
def atualizar(conta_id: int):
    data = request.get_json(silent=True) or {}
    codigo = (data.get("codigo") or "").strip()
    nome = (data.get("nome") or "").strip()
    tipo = data.get("tipo") or "receita"
    if not codigo or not nome:
        return jsonify({"error": "Informe código e nome da conta"}), 400
    if tipo not in ("receita", "despesa"):
        return jsonify({"error": "Tipo deve ser receita ou despesa"}), 400
    ok = plano_conta_repo.update(conta_id, codigo, nome, tipo, data.get("pai_id") or None)
    if not ok:
        return jsonify({"error": "Conta não encontrada"}), 404
    return jsonify({"ok": True})


@api_plano_contas_bp.patch("/api/plano-contas/<int:conta_id>/ativo")
def alternar_ativo(conta_id: int):
    ativo = request.args.get("ativo", "").lower() in ("1", "true")
    ok = plano_conta_repo.set_ativo(conta_id, ativo)
    if not ok:
        return jsonify({"error": "Conta não encontrada"}), 404
    return jsonify({"ok": True})