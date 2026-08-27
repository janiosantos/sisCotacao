"""Portal público do fornecedor (autosserviço, sem login).

O fornecedor acessa /fornecedor/<token>, vê os itens solicitados e envia a
proposta (preço, desconto, prazo, disponibilidade). Tudo sem autenticação.
"""
from __future__ import annotations

from flask import Blueprint, jsonify, render_template, request

from catalog_server.repositories import catalog_repo, compras_repo
from catalog_server.utils import image_url

portal_bp = Blueprint("portal", __name__)


@portal_bp.get("/fornecedor/<token>")
def portal_pagina(token: str):
    return render_template("fornecedor_portal.html", token=token)


@portal_bp.get("/api/fornecedor/<token>")
def portal_dados(token: str):
    ctx = compras_repo.public_portal(token)
    if ctx is None:
        return jsonify({"error": "Link inválido"}), 404
    itens = compras_repo.portal_itens(token)
    produtos = catalog_repo.products_by_ids([i["produto_id"] for i in itens])
    for i in itens:
        p = produtos.get(i["produto_id"], {})
        i["name"] = p.get("name", f"Produto #{i['produto_id']}")
        i["sku"] = p.get("sku", "")
        i["brand"] = p.get("brand", "")
        i["imagem_url"] = p.get("imagem_url")
    return jsonify({**ctx, "itens": itens})


@portal_bp.post("/api/fornecedor/<token>/proposta")
def portal_proposta(token: str):
    data = request.get_json(silent=True) or {}
    precos = data.get("precos") or []
    if not precos:
        return jsonify({"error": "Nenhuma proposta enviada"}), 400
    condicao_pagamento = data.get("condicao_pagamento")
    condicao_pagamento_dias = data.get("condicao_pagamento_dias")
    try:
        condicao_pagamento_dias = (
            int(condicao_pagamento_dias) if condicao_pagamento_dias not in (None, "") else None
        )
    except (TypeError, ValueError):
        condicao_pagamento_dias = None
    ok = compras_repo.submit_proposta(
        token, precos, condicao_pagamento, condicao_pagamento_dias
    )
    if not ok:
        return jsonify({"error": "Link inválido"}), 404
    return jsonify({"ok": True})