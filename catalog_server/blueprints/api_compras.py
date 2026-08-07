"""API do fluxo de compra em tela única (montar lista, disparar, comparar,
gerar pedidos)."""
from __future__ import annotations

from flask import Blueprint, jsonify, request

from catalog_server.repositories import compras_repo, quote_repo
from catalog_server.services import compras as compras_service

api_compras_bp = Blueprint("api_compras", __name__)


def _invites_com_links(invites: list[dict], comprador: str, apelido: str, data_limite: str) -> list[dict]:
    out = []
    for inv in invites:
        link = compras_service.fornecedor_link(inv["token"])
        d = dict(inv)
        d["link"] = link
        d["whatsapp_url"] = ""
        d["mailto_url"] = ""
        if inv["whatsapp"]:
            msg = compras_service.mensagem_whatsapp(
                comprador, inv["representante"] or inv["nome"], link,
                apelido, data_limite,
            )
            d["whatsapp_url"] = compras_service.whatsapp_url(inv["whatsapp"], msg)
        if inv["email"]:
            d["mailto_url"] = compras_service.mailto_url(
                inv["email"], compras_service.email_assunto(apelido, None), link,
            )
        out.append(d)
    return out


@api_compras_bp.post("/api/compras/cotacoes")
def criar_cotacao_compras():
    data = request.get_json(silent=True) or {}
    itens = data.get("itens") or []
    if not itens:
        return jsonify({"error": "Adicione ao menos 1 item à lista"}), 400
    apelido = (data.get("apelido") or "").strip()
    if not apelido:
        apelido = "Cotação de compra"
    fornecedores = data.get("fornecedores") or []
    if not fornecedores:
        return jsonify({"error": "Convide ao menos 1 fornecedor"}), 400
    for i in itens:
        if not i.get("produto_id"):
            return jsonify({"error": "Item sem produto válido"}), 400
    try:
        cotacao_id, numero = compras_repo.create_rfq(
            apelido,
            (data.get("data_limite") or "").strip(),
            (data.get("comprador") or "").strip(),
            itens,
            fornecedores,
        )
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    compras_repo.ensure_tokens(cotacao_id)
    invites = compras_repo.get_invites(cotacao_id)
    return jsonify({
        "id": cotacao_id,
        "numero": numero,
        "invites": _invites_com_links(invites, data.get("comprador") or "",
                                      apelido, data.get("data_limite") or ""),
    })


@api_compras_bp.get("/api/compras/cotacoes/<int:cotacao_id>/invites")
def convites(cotacao_id: int):
    compras_repo.ensure_tokens(cotacao_id)
    invites = compras_repo.get_invites(cotacao_id)
    dados = quote_repo.get(cotacao_id)
    cot = dados["cotacao"] if dados else {}
    return jsonify(_invites_com_links(invites, cot.get("cliente") or "",
                                      cot.get("titulo") or "",
                                      cot.get("data_limite_retorno") or ""))


@api_compras_bp.get("/api/compras/cotacoes/<int:cotacao_id>/comparar")
def comparar(cotacao_id: int):
    matriz = compras_service.montar_matriz(cotacao_id)
    if matriz is None:
        return jsonify({"error": "Cotação não encontrada"}), 404
    return jsonify(matriz)


@api_compras_bp.post("/api/compras/cotacoes/<int:cotacao_id>/pedidos")
def gerar_pedidos(cotacao_id: int):
    data = request.get_json(silent=True) or {}
    logica = data.get("logica", "fracionado")
    pedidos = compras_repo.gerar_pedidos(cotacao_id, logica)
    return jsonify({"pedidos": pedidos})


@api_compras_bp.get("/api/compras/pedidos")
def listar_pedidos():
    return jsonify(compras_repo.list_pedidos())


@api_compras_bp.get("/api/compras/pedidos/<int:pedido_id>")
def detalhar_pedido(pedido_id: int):
    pedido = compras_repo.get_pedido(pedido_id)
    if pedido is None:
        return jsonify({"error": "Pedido não encontrado"}), 404
    return jsonify(pedido)