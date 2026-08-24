from __future__ import annotations

from flask import Blueprint, jsonify, request
from catalog_server.repositories import fornecedor_preco_repo, fornecedor_preferencial_repo, solicitacao_repo, tolerancia_repo
from catalog_server.services import custo_engine

api_compras_avancado_bp = Blueprint("api_compras_avancado", __name__)


# ─── Custo líquido (Motor Fiscal → Custo) ──────────────────

@api_compras_avancado_bp.get("/api/custos/calcular/<int:variante_id>")
def calcular_custo(variante_id: int):
    fornecedor_id = request.args.get("fornecedor_id", type=int)
    return jsonify(custo_engine.calcular_custo(variante_id, fornecedor_id=fornecedor_id))


@api_compras_avancado_bp.get("/api/fornecedor-preco")
def listar_precos():
    return jsonify(fornecedor_preco_repo.list(
        fornecedor_id=request.args.get("fornecedor_id", type=int),
        variante_id=request.args.get("variante_id", type=int),
    ))


@api_compras_avancado_bp.post("/api/fornecedor-preco")
def upsert_preco():
    data = request.get_json(silent=True) or {}
    f_id = data.get("fornecedor_id")
    v_id = data.get("variante_id")
    preco = data.get("preco")
    if not f_id or not v_id or preco is None:
        return jsonify({"error": "fornecedor_id, variante_id e preco obrigatórios"}), 400
    return jsonify({"id": fornecedor_preco_repo.upsert(
        f_id, v_id, float(preco),
        data.get("prazo_entrega"), float(data.get("icms") or 0), float(data.get("ipi") or 0),
    )}), 201


@api_compras_avancado_bp.get("/api/solicitacoes-compra")
def listar_solicitacoes():
    return jsonify(solicitacao_repo.list(status=request.args.get("status")))


@api_compras_avancado_bp.get("/api/solicitacoes-compra/<int:sc_id>")
def detalhar_solicitacao(sc_id: int):
    sc = solicitacao_repo.get(sc_id)
    if sc is None:
        return jsonify({"error": "Solicitação não encontrada"}), 404
    return jsonify(sc)


@api_compras_avancado_bp.post("/api/solicitacoes-compra")
def criar_solicitacao():
    data = request.get_json(silent=True) or {}
    sc_id = solicitacao_repo.create(
        data.get("codigo", ""), data.get("descricao", ""),
        data.get("observacao", ""), data.get("usuario_id"),
    )
    return jsonify({"id": sc_id}), 201


@api_compras_avancado_bp.post("/api/solicitacoes-compra/<int:sc_id>/itens")
def add_item_solicitacao(sc_id: int):
    data = request.get_json(silent=True) or {}
    v_id = data.get("variante_id")
    qtd = data.get("quantidade")
    if not v_id or not qtd:
        return jsonify({"error": "variante_id e quantidade obrigatórios"}), 400
    return jsonify({"id": solicitacao_repo.add_item(
        sc_id, v_id, float(qtd), data.get("justificativa", ""),
    )}), 201


@api_compras_avancado_bp.get("/api/fornecedor-preferencial")
def listar_preferenciais():
    return jsonify(fornecedor_preferencial_repo.list(variante_id=request.args.get("variante_id", type=int)))


@api_compras_avancado_bp.post("/api/fornecedor-preferencial")
def upsert_preferencial():
    data = request.get_json(silent=True) or {}
    v_id = data.get("variante_id")
    f_id = data.get("fornecedor_id")
    if not v_id or not f_id:
        return jsonify({"error": "variante_id e fornecedor_id obrigatórios"}), 400
    return jsonify({"id": fornecedor_preferencial_repo.upsert(
        v_id, f_id, int(data.get("ranking", 1)),
        float(data["ultimo_preco"]) if data.get("ultimo_preco") else None,
        int(data["ultimo_prazo"]) if data.get("ultimo_prazo") else None,
    )}), 201


@api_compras_avancado_bp.get("/api/tolerancias-compra")
def get_tolerancia():
    f_id = request.args.get("fornecedor_id", type=int)
    if not f_id:
        return jsonify({"error": "fornecedor_id obrigatório"}), 400
    t = tolerancia_repo.get(f_id)
    return jsonify(t or {})


@api_compras_avancado_bp.post("/api/tolerancias-compra")
def upsert_tolerancia():
    data = request.get_json(silent=True) or {}
    f_id = data.get("fornecedor_id")
    if not f_id:
        return jsonify({"error": "fornecedor_id obrigatório"}), 400
    return jsonify({"id": tolerancia_repo.upsert(
        f_id, float(data.get("tolerancia_preco_pct", 10)),
        float(data.get("tolerancia_qtd_pct", 10)), data.get("exige_aprovacao", True),
    )}), 201
