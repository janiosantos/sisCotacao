"""Proxy para o microserviço "Cotações IA Importer" + aplicação no catálogo.

- Extração (texto/PDF) e matching (Qdrant) são delegados ao microserviço.
- O seed envia o catálogo REAL das variantes (crawler.db) para o Qdrant.
- O apply grava os preços importados nas cotações existentes via registrar_preco.
"""

from __future__ import annotations

from flask import Blueprint, jsonify, request

from catalog_server.config import IA_SEED_LIMIT
from catalog_server.repositories import catalog_repo, quote_repo
from catalog_server.services import importer

api_ia_bp = Blueprint("api_ia", __name__)


# ----------------------------------------------------------------------
# Diagnóstico
# ----------------------------------------------------------------------


@api_ia_bp.get("/api/ia/health")
def ia_health():
    if importer.health():
        return jsonify({"ok": True})
    return jsonify({"ok": False, "error": f"Microserviço IA indisponível em {importer.API}"}), 503


# ----------------------------------------------------------------------
# Seed do Qdrant com o catálogo real
# ----------------------------------------------------------------------


@api_ia_bp.post("/api/ia/seed")
def ia_seed():
    data = request.get_json(silent=True) or {}
    reset = bool(data.get("reset"))
    max_linhas = IA_SEED_LIMIT

    cards, total = catalog_repo.list_products(agrupado=False, em_linha=True, limit=max_linhas)
    produtos = [{"id": c["id"], "name": c["name"]} for c in cards if c.get("name")]
    if not produtos:
        return jsonify({"error": "Catálogo vazio para o seed."}), 400

    cv: dict = importer.seed(produtos, reset=reset)
    return jsonify(
        {
            "enviados": len(produtos),
            "populados": cv.get("populados"),
            "total_catalogo": total,
            "cap": max_linhas,
            "troncado": total > max_linhas,
            "colecao": cv.get("collection"),
        }
    )


# ----------------------------------------------------------------------
# Extração (texto / PDF)
# ----------------------------------------------------------------------


@api_ia_bp.post("/api/ia/extract")
def ia_extract():
    data = request.get_json(silent=True) or {}
    texto = (data.get("text") or "").strip()
    if not texto:
        return jsonify({"error": "Texto vazio."}), 400
    return jsonify(importer.extract(texto))


@api_ia_bp.post("/api/ia/extract/file")
def ia_extract_file():
    arquivo = request.files.get("file")
    if not arquivo or not arquivo.filename:
        return jsonify({"error": "Envie um arquivo no campo 'file'."}), 400
    dados = arquivo.read()
    if not dados:
        return jsonify({"error": "Arquivo vazio."}), 400
    try:
        return jsonify(importer.extract_pdf(dados, arquivo.filename or "arquivo.pdf"))
    except importer.ImporterError as exc:
        return jsonify({"error": str(exc)}), 502


# ----------------------------------------------------------------------
# Matching (Top-K no catálogo real)
# ----------------------------------------------------------------------


@api_ia_bp.post("/api/ia/match")
def ia_match():
    data = request.get_json(silent=True) or {}
    itens = data.get("items") or []
    if not isinstance(itens, list) or not itens:
        return jsonify({"error": "Lista de itens vazia."}), 400
    try:
        return jsonify(importer.match(itens, limite=int(data.get("top_k", 5))))
    except importer.ImporterError as exc:
        return jsonify({"error": str(exc)}), 502


# ----------------------------------------------------------------------
# Aplicação na cotação
# ----------------------------------------------------------------------


@api_ia_bp.post("/api/ia/apply")
def ia_apply():
    data = request.get_json(silent=True) or {}
    cotacao_id = data.get("cotacao_id")
    fornecedor_id = data.get("fornecedor_id")
    selecoes = data.get("selections") or []

    def error(msg, code):
        return jsonify({"error": msg}), code

    if cotacao_id is None:
        return error("cotacao_id é obrigatório.", 400)
    if fornecedor_id is None:
        return error("fornecedor_id é obrigatório.", 400)
    if not isinstance(selecoes, list) or not selecoes:
        return error("Selecione pelo menos um item com candidato.", 400)

    aplicados, ignorados = 0, []
    for sel in selecoes:
        produto_id = sel.get("produto_id")
        preco = sel.get("preco_extraido")
        if produto_id is None or preco is None:
            ignorados.append({"produto_fornecedor": sel.get("produto_fornecedor", "?"), "motivo": "sem produto/preço"})
            continue
        try:
            preco_num = float(preco)
        except (TypeError, ValueError):
            ignorados.append({"produto_fornecedor": sel.get("produto_fornecedor", "?"), "motivo": "preço inválido"})
            continue
        item_id = quote_repo.item_por_produto(int(cotacao_id), int(produto_id))
        if item_id is None:
            ignorados.append(
                {"produto_fornecedor": sel.get("produto_fornecedor", "?"), "motivo": "produto não está nesta cotação"}
            )
            continue
        quote_repo.registrar_preco(
            int(cotacao_id),
            item_id,
            int(fornecedor_id),
            preco_num,
            0,
            (f"IA: {sel.get('produto_fornecedor')}" if sel.get("produto_fornecedor") else "IA: importado"),
            None,
        )
        aplicados += 1

    return jsonify({"aplicados": aplicados, "ignorados": ignorados})