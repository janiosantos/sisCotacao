from __future__ import annotations

from flask import Blueprint, jsonify, request

from catalog_server.db import system_conn
from catalog_server.repositories import catalog_repo

api_publico_bp = Blueprint("api_publico", __name__)

# API pública (somente leitura) para o site institucional exibir o catálogo.
# Não exige token. Expõe APENAS campos seguros — nunca custo, NCM,
# fornecedores, classe ABC ou dados internos do ERP.


def _sanitizar(card: dict) -> dict:
    """Converte um card do catálogo (contrato interno) para o contrato público."""
    return {
        "id": card.get("id"),
        "sku": card.get("sku") or "",
        "ean": card.get("ean") or "",
        "nome": card.get("name") or "",
        "marca": card.get("brand") or "",
        "grupo": card.get("grupo") or "",
        "grupo_nome": card.get("grupo_nome") or "",
        "categoria": card.get("category") or "",
        "subcategoria": card.get("subcategoria") or "",
        "preco": card.get("price") or 0,
        "preco_promocional": card.get("old_price"),
        "pix_price": card.get("pix_price") or 0,
        "unidade_venda": card.get("unidade_venda") or "",
        "embalagem_qtd": card.get("embalagem_qtd"),
        "especificacoes": card.get("spec") or "",
        "descricao": card.get("descricao") or "",
        "atributos": card.get("attrs") or {},
        "imagem_url": card.get("imagem_url"),
    }


@api_publico_bp.route("/api/publico/produtos", methods=["GET", "OPTIONS"])
def publico_produtos():
    if request.method == "OPTIONS":
        return ("", 204)
    offset = max(0, request.args.get("offset", 0, type=int))
    limit = min(100, max(1, request.args.get("limit", 30, type=int)))
    items, total = catalog_repo.list_products(
        categoria=(request.args.get("categoria") or "").strip(),
        subcategoria=(request.args.get("subcategoria") or "").strip(),
        grupo=(request.args.get("grupo") or "").strip(),
        q=(request.args.get("q") or "").strip(),
        em_linha=request.args.get("em_linha", "1") != "0",
        offset=offset,
        limit=limit,
        agrupado=False,
    )
    return jsonify(
        {
            "items": [_sanitizar(c) for c in items],
            "total": total,
            "offset": offset,
            "limit": limit,
            "has_more": offset + limit < total,
        }
    )


@api_publico_bp.route("/api/publico/produtos/<int:produto_id>", methods=["GET", "OPTIONS"])
def publico_produto(produto_id: int):
    if request.method == "OPTIONS":
        return ("", 204)
    p = catalog_repo.product(produto_id)
    if p is None:
        return jsonify({"error": "Produto não encontrado"}), 404
    grupo_codigo = grupo_nome = ""
    with system_conn() as conn:
        row = conn.execute(
            "SELECT descricao, unidade_venda, embalagem, atributos, grupo_id"
            " FROM produtos_cadastro WHERE id=?",
            (produto_id,),
        ).fetchone()
        if row and row["grupo_id"]:
            g = conn.execute(
                "SELECT codigo, nome FROM grupos WHERE id=?",
                (row["grupo_id"],),
            ).fetchone()
            if g:
                grupo_codigo, grupo_nome = g["codigo"], g["nome"]
    imagens = p.get("image_urls") or []
    return jsonify(
        {
            "id": p["id"],
            "sku": p.get("sku") or "",
            "ean": p.get("ean") or "",
            "nome": p.get("name") or "",
            "marca": p.get("brand") or "",
            "cor": p.get("color") or "",
            "grupo": grupo_codigo,
            "grupo_nome": grupo_nome,
            "categoria": p.get("category") or "",
            "subcategoria": p.get("subcategoria") or "",
            "preco": p.get("price") or 0,
            "preco_promocional": p.get("old_price"),
            "pix_price": p.get("pix_price") or 0,
            "parcelamento": p.get("installment") or "",
            "unidade_venda": (row["unidade_venda"] if row else None) or "",
            "embalagem_qtd": (row["embalagem"] if row else None) or "",
            "descricao": ((row["descricao"] if row else "") or "").strip(),
            "atributos": (row["atributos"] if row else None) or {},
            "imagem_url": imagens[0] if imagens else None,
            "imagens": imagens,
        }
    )


@api_publico_bp.route("/api/publico/categorias", methods=["GET", "OPTIONS"])
def publico_categorias():
    if request.method == "OPTIONS":
        return ("", 204)
    return jsonify(catalog_repo.categorias())


@api_publico_bp.route("/api/publico/marcas", methods=["GET", "OPTIONS"])
def publico_marcas():
    if request.method == "OPTIONS":
        return ("", 204)
    with system_conn() as conn:
        rows = conn.execute(
            "SELECT DISTINCT marca FROM produtos_cadastro"
            " WHERE ativo=1 AND marca IS NOT NULL AND trim(marca)<>''"
            " ORDER BY marca"
        ).fetchall()
    return jsonify({"marcas": [r["marca"] for r in rows]})


@api_publico_bp.route("/api/publico/grupos", methods=["GET", "OPTIONS"])
def publico_grupos():
    if request.method == "OPTIONS":
        return ("", 204)
    with system_conn() as conn:
        rows = conn.execute(
            """
            SELECT g.codigo, g.nome, COUNT(p.id) AS total
            FROM grupos g
            LEFT JOIN produtos_cadastro p ON p.grupo_id=g.id AND p.ativo=1
            WHERE g.ativo=1
            GROUP BY g.id, g.codigo, g.nome
            ORDER BY g.codigo
            """
        ).fetchall()
    return jsonify(
        {"grupos": [{"codigo": r["codigo"], "nome": r["nome"], "total": r["total"]} for r in rows]}
    )