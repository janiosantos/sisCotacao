from __future__ import annotations

from flask import Blueprint, jsonify, request

from catalog_server import abc
from catalog_server.repositories import catalog_repo

api_catalog_bp = Blueprint("api_catalog", __name__)


@api_catalog_bp.get("/api/categorias")
def categorias():
    return jsonify(catalog_repo.categorias())


@api_catalog_bp.get("/api/produtos")
def listar_produtos():
    offset = max(0, request.args.get("offset", 0, type=int))
    limit = min(200, max(1, request.args.get("limit", 60, type=int)))
    classe = (request.args.get("classe") or "").strip().upper()
    if classe not in ("A", "B", "C"):
        classe = ""
    items, total = catalog_repo.list_products(
        categoria=(request.args.get("categoria") or "").strip(),
        subcategoria=(request.args.get("subcategoria") or "").strip(),
        grupo=(request.args.get("grupo") or "").strip(),
        q=(request.args.get("q") or "").strip(),
        classe=classe,
        em_linha=request.args.get("em_linha", "1") != "0",
        offset=offset,
        limit=limit,
        agrupado=request.args.get("agrupado", "1") != "0",
        ordenar=(request.args.get("ordenar") or "").strip(),
    )
    return jsonify({"items": items, "total": total, "offset": offset, "limit": limit})


@api_catalog_bp.get("/api/produtos/abc-resumo")
def produtos_abc_resumo():
    """Contagem de produtos por classe ABC sob os filtros atuais do catálogo."""
    return jsonify(
        catalog_repo.resumo_abc(
            categoria=(request.args.get("categoria") or "").strip(),
            subcategoria=(request.args.get("subcategoria") or "").strip(),
            grupo=(request.args.get("grupo") or "").strip(),
            q=(request.args.get("q") or "").strip(),
            em_linha=request.args.get("em_linha", "1") != "0",
        )
    )


@api_catalog_bp.get("/api/produtos/abc")
def produtos_abc():
    """Prioridade de cotação (RFQ): Classe A primeiro, por impacto financeiro.

    Restrito ao rolar em foco (`em_linha=1`, exclui equipamentos de alto
    valor). Query params opcionais: `classe=A,B,C` (default A), `linha`
    (repetível), `limit`.
    """
    classes = tuple(
        c.strip().upper()
        for c in (request.args.get("classe") or "A").split(",")
        if c.strip().upper() in ("A", "B", "C")
    ) or ("A",)
    linhas = tuple(
        l.strip() for l in request.args.getlist("linha") if l.strip()
    )
    limit = max(0, request.args.get("limit", 0, type=int))
    itens = abc.prioridade_cotacao(classes=classes, linhas=linhas, limit=limit)
    return jsonify({"classes": list(classes), "total": len(itens), "items": itens})


@api_catalog_bp.get("/api/produtos/<int:product_id>")
def produto(product_id: int):
    product = catalog_repo.product(product_id)
    if product is None:
        return jsonify({"error": "Produto não encontrado"}), 404
    return jsonify(product)
