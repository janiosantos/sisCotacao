from __future__ import annotations

from flask import Blueprint, abort, render_template, send_from_directory

from catalog_server.config import PROJECT_DIR
from catalog_server.repositories import catalog_repo, compras_repo, quote_repo
from catalog_server.services import quote_service
from catalog_server.blueprints.api_quotes import _enrich_itens

pages_bp = Blueprint("pages", __name__)

# Build do frontend (Vite+TS); fonte única da SPA.
FRONTEND_DIST = PROJECT_DIR / "frontend" / "dist"


def _frontend_ready() -> bool:
    return (FRONTEND_DIST / "index.html").is_file()


@pages_bp.get("/")
def index():
    if _frontend_ready():
        resp = send_from_directory(FRONTEND_DIST, "index.html")
        resp.headers["Cache-Control"] = "no-cache"
        return resp
    abort(503, description="Frontend não compilado — rode `npm run build` em frontend/.")


@pages_bp.get("/<path:path>")
def spa_fallback(path: str):
    """Serve o build do frontend com fallback SPA.

    Caminhos reais (assets hasheadados, etc.) são servidos do disco; qualquer
    outro caminho cai no index.html para o roteador de hash funcionar.
    """
    if not _frontend_ready():
        abort(404)
    candidate = FRONTEND_DIST / path
    if candidate.is_file():
        return send_from_directory(FRONTEND_DIST, path)
    return send_from_directory(FRONTEND_DIST, "index.html")


@pages_bp.get("/orcamentos/<int:cotacao_id>/imprimir")
def quote_print(cotacao_id: int):
    data = quote_repo.get(cotacao_id)
    if data is None:
        abort(404)
    itens = _enrich_itens(data["itens"])
    doc = quote_service.document_context(
        data["cotacao"], itens, data["fornecedores"], data["vencedores"]
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
    return render_template("pedido_print.html", pedido=pedido)
