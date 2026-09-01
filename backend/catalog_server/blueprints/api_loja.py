"""API de operações da loja (PDV/estoque/compras/pós-venda)."""
from __future__ import annotations

from flask import Blueprint, jsonify, request

from catalog_server.blueprints.api_usuarios import usuario_id_requisicao
from catalog_server.repositories import loja

api_loja_bp = Blueprint("api_loja", __name__)


@api_loja_bp.get("/api/loja/config")
def get_config():
    return jsonify(loja.get_config())


@api_loja_bp.put("/api/loja/config")
def put_config():
    data = request.get_json(silent=True) or {}
    out = {}
    for chave in ("bloquear_venda_sem_estoque", "bloquear_venda_sem_credito", "bloquear_venda_com_atraso"):
        if chave in data:
            out[chave] = bool(data[chave])
    return jsonify(loja.set_config(out))


@api_loja_bp.get("/api/loja/saldo/<int:produto_id>")
def saldo(produto_id: int):
    return jsonify({"saldos": loja.saldo_variante(produto_id),
                    "disponivel": sum(s["disponivel"] for s in loja.saldo_variante(produto_id))})


@api_loja_bp.patch("/api/loja/variante/<int:produto_id>")
def atualizar_variante(produto_id: int):
    data = request.get_json(silent=True) or {}
    if not loja.atualizar_variante_logistica(produto_id, data):
        return jsonify({"error": "Nenhum campo válido ou variante não encontrada"}), 400
    return jsonify({"ok": True})


@api_loja_bp.patch("/api/loja/estoque/<int:produto_id>/<int:deposito_id>")
def atualizar_estoque(produto_id: int, deposito_id: int):
    data = request.get_json(silent=True) or {}
    if not loja.atualizar_estoque_localizacao(produto_id, deposito_id, data):
        return jsonify({"error": "Nenhum campo válido"}), 400
    return jsonify({"ok": True})


# ─── Inventário ───────────────────────────────────────────

@api_loja_bp.get("/api/loja/inventarios")
def listar_inventarios():
    return jsonify(loja.listar_inventarios())


@api_loja_bp.post("/api/loja/inventarios")
def criar_inventario():
    data = request.get_json(silent=True) or {}
    if not (data.get("nome") or "").strip():
        return jsonify({"error": "Informe o nome do inventário"}), 400
    return jsonify({"id": loja.criar_inventario(data["nome"], data.get("deposito_id"))}), 201


@api_loja_bp.get("/api/loja/inventarios/<int:inventario_id>/itens")
def itens_inventario(inventario_id: int):
    return jsonify(loja.itens_inventario(inventario_id))


@api_loja_bp.patch("/api/loja/inventarios/<int:inventario_id>/itens/<int:item_id>")
def contar_item(inventario_id: int, item_id: int):
    data = request.get_json(silent=True) or {}
    if not loja.registrar_contagem(inventario_id, item_id, float(data.get("quantidade_contada") or 0)):
        return jsonify({"error": "Item não encontrado"}), 404
    return jsonify({"ok": True})


@api_loja_bp.post("/api/loja/inventarios/<int:inventario_id>/finalizar")
def finalizar_inventario(inventario_id: int):
    return jsonify(loja.finalizar_inventario(inventario_id))


# ─── Reposição ────────────────────────────────────────────

@api_loja_bp.get("/api/loja/reposicao")
def reposicao():
    return jsonify(loja.reposicao())


# ─── Devolução/troca ──────────────────────────────────────

@api_loja_bp.get("/api/loja/devolucoes")
def listar_devolucoes():
    return jsonify(loja.listar_devolucoes())


@api_loja_bp.post("/api/loja/devolucoes")
def registrar_devolucao():
    data = request.get_json(silent=True) or {}
    if not data.get("produto_id") or not data.get("quantidade"):
        return jsonify({"error": "produto_id e quantidade obrigatórios"}), 400
    dev_id = loja.registrar_devolucao(
        orcamento_id=data.get("orcamento_id"),
        produto_id=int(data["produto_id"]),
        quantidade=float(data["quantidade"]),
        motivo=data.get("motivo", ""),
        tipo=data.get("tipo", "devolucao"),
        deposito_id=data.get("deposito_id", 1),
        usuario_id=usuario_id_requisicao(),
    )
    return jsonify({"id": dev_id}), 201


@api_loja_bp.patch("/api/loja/devolucoes/<int:devolucao_id>")
def alterar_status_devolucao(devolucao_id: int):
    data = request.get_json(silent=True) or {}
    if not loja.alterar_status_devolucao(devolucao_id, data.get("status", "")):
        return jsonify({"error": "Status inválido ou devolução não encontrada"}), 400
    return jsonify({"ok": True})


# ─── Comissão ─────────────────────────────────────────────

@api_loja_bp.get("/api/loja/comissoes")
def comissoes():
    return jsonify(loja.comissoes(
        inicio=request.args.get("inicio"), fim=request.args.get("fim"),
    ))


# ─── Etiquetas (dados) ────────────────────────────────────

@api_loja_bp.get("/api/loja/etiquetas")
def dados_etiquetas():
    ids = [int(x) for x in (request.args.get("ids") or "").split(",") if x.strip().isdigit()]
    return jsonify(loja.dados_etiquetas(ids))
