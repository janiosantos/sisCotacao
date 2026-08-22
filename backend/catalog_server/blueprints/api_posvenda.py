from __future__ import annotations

from flask import Blueprint, jsonify, request

from catalog_server.repositories import garantia_repo, interacao_repo

api_posvenda_bp = Blueprint("api_posvenda", __name__)


# ─── Interações ────────────────────────────────────────────

@api_posvenda_bp.get("/api/posvenda/interacoes")
def listar_interacoes():
    cliente_id = request.args.get("cliente_id", type=int)
    pendentes = request.args.get("pendentes", "").lower() in ("1", "true")
    return jsonify(interacao_repo.list(cliente_id=cliente_id, pendentes=pendentes))


@api_posvenda_bp.post("/api/posvenda/interacoes")
def criar_interacao():
    data = request.get_json(silent=True) or {}
    cliente_nome = (data.get("cliente_nome") or "").strip()
    tipo = (data.get("tipo") or "").strip()
    descricao = (data.get("descricao") or "").strip()
    data_contato = data.get("data_contato")
    if not cliente_nome or not tipo or not data_contato:
        return jsonify({"error": "cliente_nome, tipo e data_contato obrigatórios"}), 400
    if tipo not in ("ligacao", "visita", "email", "whatsapp", "follow_up", "outro"):
        return jsonify({"error": "tipo inválido"}), 400
    interacao_id = interacao_repo.create(
        cliente_id=data.get("cliente_id"),
        cliente_nome=cliente_nome, tipo=tipo, descricao=descricao,
        data_contato=data_contato,
        data_proximo_contato=data.get("data_proximo_contato"),
        orcamento_id=data.get("orcamento_id"),
        usuario_id=data.get("usuario_id"),
    )
    return jsonify({"id": interacao_id}), 201


# ─── Garantia ──────────────────────────────────────────────

@api_posvenda_bp.get("/api/posvenda/garantias")
def listar_garantias():
    cliente_id = request.args.get("cliente_id", type=int)
    status = request.args.get("status") or None
    return jsonify(garantia_repo.list(cliente_id=cliente_id, status=status))


@api_posvenda_bp.post("/api/posvenda/garantias")
def criar_garantia():
    data = request.get_json(silent=True) or {}
    cliente_nome = (data.get("cliente_nome") or "").strip()
    produto_nome = (data.get("produto_nome") or "").strip()
    data_inicio = data.get("data_inicio")
    data_fim = data.get("data_fim")
    if not cliente_nome or not produto_nome or not data_inicio or not data_fim:
        return jsonify({"error": "cliente_nome, produto_nome, data_inicio e data_fim obrigatórios"}), 400
    garantia_id = garantia_repo.create(
        cliente_nome, produto_nome, data_inicio, data_fim,
        dias=int(data.get("dias", 90)),
        cliente_id=data.get("cliente_id"),
        orcamento_id=data.get("orcamento_id"),
        variante_id=data.get("variante_id"),
        descricao=data.get("descricao", ""),
        observacao=data.get("observacao", ""),
        data_venda=data.get("data_venda"),
    )
    return jsonify({"id": garantia_id}), 201


@api_posvenda_bp.patch("/api/posvenda/garantias/<int:garantia_id>/status")
def atualizar_status_garantia(garantia_id: int):
    data = request.get_json(silent=True) or {}
    status = (data.get("status") or "").strip()
    if status not in ("ativa", "vencida", "acionada", "cancelada"):
        return jsonify({"error": "status inválido"}), 400
    if not garantia_repo.update_status(garantia_id, status):
        return jsonify({"error": "Garantia não encontrada"}), 404
    return jsonify({"ok": True})
