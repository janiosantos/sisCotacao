from __future__ import annotations

from flask import Blueprint, jsonify, request

from catalog_server.repositories import catalog_repo, produto_repo, quote_repo
from catalog_server.services import quote_service

api_quotes_bp = Blueprint("api_quotes", __name__)


def _enrich_itens(itens: list[dict]) -> list[dict]:
    products = catalog_repo.products_by_ids([i["produto_id"] for i in itens])
    enriched = []
    for i in itens:
        p = products.get(i["produto_id"], {})
        desc = i.get("descricao") or ""
        enriched.append(
            {
                "cotacao_item_id": i["id"],
                "produto_id": i["produto_id"],
                "quantidade": i["quantidade"],
                "descricao": desc,
                "sku": p.get("sku", ""),
                "name": desc or p.get("name", f"Produto #{i['produto_id']}"),
                "brand": p.get("brand", ""),
                "category": p.get("category", ""),
                "subcategory": p.get("subcategory", ""),
                "imagem_url": p.get("imagem_url"),
                "price": p.get("price", 0),
            }
        )
    return enriched


# ----------------------------------------------------------------------
# Cotações
# ----------------------------------------------------------------------


@api_quotes_bp.get("/api/cotacoes")
def listar():
    status = (request.args.get("status") or "").strip()
    return jsonify(quote_repo.list(status))


@api_quotes_bp.post("/api/cotacoes")
def criar():
    data = request.get_json(silent=True) or {}
    itens = data.get("itens") or []
    if not itens:
        return jsonify({"error": "A cotação precisa de ao menos 1 item"}), 400
    resolved = []
    for i in itens:
        quantidade = float(i.get("quantidade", 1) or 1)
        descricao = (i.get("descricao") or "").strip()
        produto_id = i.get("produto_id")
        if produto_id:
            resolved.append({"produto_id": int(produto_id), "quantidade": quantidade, "descricao": descricao})
            continue
        # item livre: tamanho/cor fora do cadastro — cada variação é agora um
        # produto próprio em produtos_cadastro. Procura o produto da família
        # cujos atributos (JSONB) casam com os informados.
        from catalog_server.db import system_conn as _sc_q
        import json as _json

        produto_pai = i.get("produto_pai") or i.get("produto_cadastro_id")
        if not produto_pai:
            return jsonify({"error": "Item sem produto válido"}), 400
        atributos = i.get("atributos") or {}
        try:
            atributos_int = {int(k): str(v) for k, v in atributos.items() if v not in (None, "")}
        except (TypeError, ValueError):
            return jsonify({"error": "Atributos inválidos no item livre"}), 400
        with _sc_q() as _conn:
            row = _conn.execute(
                "SELECT id FROM produtos_cadastro"
                " WHERE familia_id=? AND ativo=1 AND atributos @> ?::jsonb LIMIT 1",
                (int(produto_pai), _json.dumps(atributos_int, ensure_ascii=False)),
            ).fetchone()
            vid = row["id"] if row else None
        if not vid:
            return jsonify({"error": "Nenhum produto da família corresponde aos atributos informados"}), 400
        resolved.append({"produto_id": vid, "quantidade": quantidade, "descricao": descricao})
    cotacao_id, numero = quote_repo.create(
        titulo=(data.get("titulo") or "").strip(),
        cliente=(data.get("cliente") or "").strip(),
        observacoes=(data.get("observacoes") or "").strip(),
        fornecedor_ids=[int(f) for f in (data.get("fornecedor_ids") or [])],
        itens=resolved,
    )
    return jsonify({"id": cotacao_id, "numero": numero})


@api_quotes_bp.get("/api/cotacoes/<int:cotacao_id>")
def detalhar(cotacao_id: int):
    data = quote_repo.get(cotacao_id)
    if data is None:
        return jsonify({"error": "Cotação não encontrada"}), 404
    data["itens"] = _enrich_itens(data["itens"])
    return jsonify(data)


@api_quotes_bp.patch("/api/cotacoes/<int:cotacao_id>")
def atualizar(cotacao_id: int):
    data = request.get_json(silent=True) or {}
    status = data.get("status")
    if status is not None and not quote_service.valid_status(status):
        return jsonify({"error": "Status inválido"}), 400
    quote_repo.update_fields(
        cotacao_id,
        titulo=data.get("titulo"),
        cliente=data.get("cliente"),
        observacoes=data.get("observacoes"),
        status=status,
    )
    return jsonify({"ok": True})


# ----------------------------------------------------------------------
# Fornecedores na cotação
# ----------------------------------------------------------------------


@api_quotes_bp.post("/api/cotacoes/<int:cotacao_id>/fornecedores/<int:fornecedor_id>")
def convidar(cotacao_id: int, fornecedor_id: int):
    quote_repo.add_fornecedor(cotacao_id, fornecedor_id)
    return jsonify({"ok": True})


@api_quotes_bp.delete("/api/cotacoes/<int:cotacao_id>/fornecedores/<int:fornecedor_id>")
def remover_fornecedor(cotacao_id: int, fornecedor_id: int):
    quote_repo.remove_fornecedor(cotacao_id, fornecedor_id)
    return jsonify({"ok": True})


# ----------------------------------------------------------------------
# Itens
# ----------------------------------------------------------------------


@api_quotes_bp.post("/api/cotacoes/<int:cotacao_id>/itens")
def adicionar_item(cotacao_id: int):
    data = request.get_json(silent=True) or {}
    produto_id = data.get("produto_id")
    if not produto_id:
        return jsonify({"error": "Informe o produto"}), 400
    quote_repo.add_item(
        cotacao_id,
        int(produto_id),
        float(data.get("quantidade", 1) or 1),
        descricao=(data.get("descricao") or "").strip(),
    )
    return jsonify({"ok": True})


@api_quotes_bp.patch("/api/cotacoes/<int:cotacao_id>/itens/<int:item_id>")
def atualizar_item(cotacao_id: int, item_id: int):
    data = request.get_json(silent=True) or {}
    quantidade = data.get("quantidade")
    if quantidade is None or float(quantidade) <= 0:
        return jsonify({"error": "Quantidade inválida"}), 400
    quote_repo.update_item(cotacao_id, item_id, float(quantidade))
    return jsonify({"ok": True})


@api_quotes_bp.delete("/api/cotacoes/<int:cotacao_id>/itens/<int:item_id>")
def remover_item(cotacao_id: int, item_id: int):
    quote_repo.remove_item(cotacao_id, item_id)
    return jsonify({"ok": True})


# ----------------------------------------------------------------------
# Preços por fornecedor
# ----------------------------------------------------------------------


@api_quotes_bp.put("/api/cotacoes/<int:cotacao_id>/precos")
def registrar_preco(cotacao_id: int):
    data = request.get_json(silent=True) or {}
    try:
        preco = float(data.get("preco_unitario"))
    except (TypeError, ValueError):
        return jsonify({"error": "Preço inválido"}), 400
    if preco < 0:
        return jsonify({"error": "Preço inválido"}), 400
    prazo = data.get("prazo_entrega_dias")
    quote_repo.registrar_preco(
        cotacao_id,
        int(data["cotacao_item_id"]),
        int(data["fornecedor_id"]),
        preco,
        int(prazo) if prazo not in (None, "") else None,
        (data.get("observacao") or "").strip(),
        (data.get("validade_preco_em") or "").strip() or None,
    )
    return jsonify({"ok": True})


# ----------------------------------------------------------------------
# Fechamento
# ----------------------------------------------------------------------


@api_quotes_bp.post("/api/cotacoes/<int:cotacao_id>/fechar")
def fechar(cotacao_id: int):
    data = request.get_json(silent=True) or {}
    escolhas = []
    for v in data.get("escolhas") or []:
        escolhas.append(
            {
                "cotacao_item_id": int(v["cotacao_item_id"]),
                "fornecedor_id": int(v["fornecedor_id"]),
                "preco_unitario": float(v["preco_unitario"]),
                "quantidade": float(v["quantidade"]),
            }
        )
    quote_repo.fechar(cotacao_id, escolhas)
    return jsonify({"ok": True})


@api_quotes_bp.post("/api/cotacoes/<int:cotacao_id>/reabrir")
def reabrir(cotacao_id: int):
    quote_repo.reabrir(cotacao_id)
    return jsonify({"ok": True})


# ----------------------------------------------------------------------
# Histórico de preços
# ----------------------------------------------------------------------


@api_quotes_bp.get("/api/historico-precos/produtos")
def produtos_com_historico():
    ids = quote_repo.produtos_com_historico()
    products = catalog_repo.products_by_ids(ids)
    return jsonify(
        [
            {"id": pid, "sku": products[pid]["sku"], "name": products[pid]["name"]}
            for pid in ids
            if pid in products
        ]
    )


@api_quotes_bp.get("/api/historico-precos")
def historico_precos():
    produto_id = request.args.get("produto_id", type=int)
    if not produto_id:
        return jsonify({"error": "Informe produto_id"}), 400
    return jsonify(quote_repo.historico_precos(produto_id))
