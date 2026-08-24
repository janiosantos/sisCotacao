from __future__ import annotations

from datetime import datetime, timedelta

from flask import Blueprint, abort, render_template, send_from_directory, request

from catalog_server.config import PROJECT_DIR
from catalog_server.repositories import (
    catalog_repo,
    compras_repo,
    condicao_repo,
    emitente_repo,
    orcamento_repo,
    quote_repo,
)
from catalog_server.repositories.orcamentos import resumo_desconto
from catalog_server.services import quote_service
from catalog_server.blueprints.api_quotes import _enrich_itens
from catalog_server.repositories import loja
from catalog_server.services import boletos as boleto_service

pages_bp = Blueprint("pages", __name__)

# Build do frontend (Vite+TS); fonte única da SPA.
FRONTEND_DIST = PROJECT_DIR / "frontend" / "dist"

_ORC_STATUS_LABEL = {
    "rascunho": "Rascunho",
    "ativo": "Ativo",
    "em_analise": "Em análise",
    "liberado": "Liberado",
    "finalizado": "Finalizado",
    "recebido": "Recebido",
    "cancelado": "Cancelado",
    "devolvido": "Devolvido",
}


@pages_bp.get("/etiquetas/imprimir")
def etiquetas_imprimir():
    ids = [int(x) for x in (request.args.get("ids") or "").split(",") if x.strip().isdigit()]
    etiquetas = loja.dados_etiquetas(ids)
    return render_template("etiquetas.html", etiquetas=etiquetas)


@pages_bp.get("/orcamentos/<int:cotacao_id>/imprimir")
def quote_print(cotacao_id: int):
    data = quote_repo.get(cotacao_id)
    if data is None:
        abort(404)
    itens = _enrich_itens(data["itens"])
    doc = quote_service.document_context(
        data["cotacao"], itens, data["fornecedores"], data["vencedores"], data["precos"]
    )
    return render_template("quote_print.html", doc=doc)


@pages_bp.get("/compras/pedidos/<int:pedido_id>/imprimir")
def pedido_print(pedido_id: int):
    pedido = compras_repo.get_pedido(pedido_id)
    if pedido is None:
        abort(404)
    produtos = catalog_repo.products_by_ids([i["produto_id"] for i in pedido["itens"]])
    for i in pedido["itens"]:
        p = produtos.get(i["produto_id"], {})
        i["name"] = p.get("name", f"Produto #{i['produto_id']}")
        i["sku"] = p.get("sku", "")
        i["brand"] = p.get("brand", "")
        i["imagem_url"] = p.get("imagem_url")
    emitente = emitente_repo.get()
    return render_template("pedido_print.html", pedido=pedido, emitente=emitente)


@pages_bp.get("/orcamentos/venda/<int:orcamento_id>/imprimir")
def orcamento_venda_print(orcamento_id: int):
    orc = orcamento_repo.buscar(orcamento_id)
    if orc is None:
        abort(404)
    emitente = emitente_repo.get()
    cond_nome = None
    if orc.get("condicao_pagamento_id"):
        cond = condicao_repo.get(orc["condicao_pagamento_id"])
        cond_nome = (cond or {}).get("nome")
    validade = None
    try:
        criado = datetime.strptime(str(orc["criado_em"])[:10], "%Y-%m-%d")
        validade = (criado + timedelta(days=int(orc.get("validade_dias") or 0))).strftime("%d/%m/%Y")
    except (TypeError, ValueError):
        pass
    return render_template(
        "orcamento_print.html",
        orc=orc,
        emitente=emitente,
        condicao_pagamento=cond_nome,
        validade=validade,
        status_label=_ORC_STATUS_LABEL.get(orc.get("status"), orc.get("status") or ""),
        desc_resumo=resumo_desconto(orc),
    )


@pages_bp.get("/orcamentos/<int:orcamento_id>/boleto")
def orcamento_boleto(orcamento_id: int):
    """Impressão do(s) boleto(s) das parcelas de uma venda a prazo."""
    orc = orcamento_repo.buscar(orcamento_id)
    if orc is None:
        abort(404)
    emitente = emitente_repo.get()
    parcelas = boleto_service.parcelas_com_boleto(orc.get("numero") or "")
    cond_nome = None
    if orc.get("condicao_pagamento_id"):
        cond = condicao_repo.get(orc["condicao_pagamento_id"])
        cond_nome = (cond or {}).get("nome")
    return render_template(
        "boleto_print.html",
        orc=orc,
        emitente=emitente,
        parcelas=parcelas,
        condicao_pagamento=cond_nome,
    )
