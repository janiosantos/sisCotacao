"""Proxy para o microserviço "Cotações IA Importer" + aplicação no catálogo.

- Extração (texto/PDF) e matching (Qdrant) são delegados ao microserviço.
- O seed envia o catálogo REAL das variantes (crawler.db) para o Qdrant.
- O apply grava os preços importados nas cotações existentes via registrar_preco.
"""

from __future__ import annotations

import difflib
import re
import unicodedata

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

    limite = int(data.get("top_k", 5))
    cotacao_id = data.get("cotacao_id")
    if cotacao_id is not None:
        try:
            cotacao_id = int(cotacao_id)
        except (TypeError, ValueError):
            return jsonify({"error": "cotacao_id inválido."}), 400

    try:
        if cotacao_id is not None:
            return jsonify(_match_cotacao(itens, cotacao_id, limite))
        return jsonify(importer.match(itens, limite=limite))
    except importer.ImporterError as exc:
        return jsonify({"error": str(exc)}), 502


def _match_cotacao(itens: list[dict], cotacao_id: int, limite: int) -> dict:
    """Limita os candidatos de cada item extraído aos produtos do próprio pedido.

    Em vez de buscar semelhanças no catálogo inteiro (Qdrant), o escopo é a
    lista de produtos vinculados à cotação: 1) monta o pool com os nomes, 2) ao
    escore de similaridade textual, 3) devolve apenas itens do pedido, ordenados.
    Itens cujo texto não se parece com nenhum item da cotação ficam sem candidato.
    """
    cotacao = quote_repo.get(cotacao_id)
    if not cotacao or not cotacao.get("itens"):
        return {"items": [{"produto_fornecedor": i.get("produto_fornecedor"), "preco_extraido": i.get("preco_extraido"), "candidatos": []} for i in itens]}

    ids_pedido = [i["produto_id"] for i in cotacao["itens"] if i.get("produto_id")]
    catalogo = catalog_repo.products_by_ids(ids_pedido)
    if not catalogo:
        return {"items": [{"produto_fornecedor": i.get("produto_fornecedor"), "preco_extraido": i.get("preco_extraido"), "candidatos": []} for i in itens]}

    pool = [
        {
            "id": pid,
            "texto": _normalizar(f"{d.get('name') or ''} {d.get('brand') or ''} {d.get('sku') or ''}"),
            "nome": d.get("name") or "",
        }
        for pid, d in catalogo.items()
    ]

    resp = []
    for item in itens:
        texto_origem = _normalizar(item.get("produto_fornecedor") or "")
        candidatos = []
        for p in pool:
            escore = _similaridade(texto_origem, p["texto"])
            if escore >= _MATCH_MIN:
                candidatos.append(
                    {
                        "produto_catalogo_id": p["id"],
                        "produto_catalogo_nome": p["nome"],
                        "score": round(escore, 4),
                    }
                )
        candidatos.sort(key=lambda c: c["score"], reverse=True)
        resp.append(
            {
                "produto_fornecedor": item.get("produto_fornecedor"),
                "preco_extraido": item.get("preco_extraido"),
                "candidatos": candidatos[:limite],
            }
        )
    return {"items": resp}


_MATCH_MIN = 0.35


def _normalizar(texto: str) -> str:
    texto = unicodedata.normalize("NFKD", texto or "").encode("ascii", "ignore").decode()
    texto = texto.lower()
    return re.sub(r"[^a-z0-9]+", " ", texto).strip()


def _similaridade(a: str, b: str) -> float:
    if not a or not b:
        return 0.0
    ratio = difflib.SequenceMatcher(None, a, b).ratio()
    ta = {_token_key(t) for t in a.split()}
    tb = {_token_key(t) for t in b.split()}
    if not ta or not tb:
        return ratio
    inter = len(ta & tb)
    jaccard = inter / len(ta | tb)
    return 0.65 * ratio + 0.35 * jaccard


def _token_key(token: str) -> str:
    """Chave de token que aproxima variantes numéricas (ex.: '3t' e '3', '4t' e '4')."""
    m = re.match(r"\d+", token)
    if m:
        return "n" + m.group()
    return token.strip(".-_")[-20:]


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