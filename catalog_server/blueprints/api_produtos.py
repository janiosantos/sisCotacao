"""API do cadastro de produtos (famílias, produtos, variações e imagens)."""
from __future__ import annotations

import requests
from flask import Blueprint, jsonify, request

from catalog_server.repositories import produto_repo
from catalog_server.services import imagens_service, parse_url_service
from catalog_server import categorias as cat_svc, unidades as unidades_svc
from catalog_server.db import system_conn
from catalog_server.utils import image_url

api_produtos_bp = Blueprint("api_produtos", __name__)


def _serialize(produto_id: int, prod: dict) -> dict:
    for img in prod.get("imagens", []):
        img["url"] = image_url(img["filename"])
        img.pop("filename", None)
    return prod


# ----------------------------------------------------------------------
# Famílias
# ----------------------------------------------------------------------

@api_produtos_bp.get("/api/familias")
def list_familias():
    incluir_inativas = request.args.get("incluir_inativas", "").lower() in ("1", "true")
    return jsonify(produto_repo.list_familias(incluir_inativas=incluir_inativas))


@api_produtos_bp.post("/api/familias")
def create_familia():
    data = request.get_json(silent=True) or {}
    nome = (data.get("nome") or "").strip()
    if not nome:
        return jsonify({"error": "Informe o nome da família"}), 400
    familia_id = produto_repo.create_familia(
        nome, (data.get("descricao") or "").strip(), data.get("atributos") or []
    )
    return jsonify({"id": familia_id}), 201


@api_produtos_bp.get("/api/familias/<int:familia_id>")
def get_familia(familia_id: int):
    familia = produto_repo.get_familia(familia_id)
    if familia is None:
        return jsonify({"error": "Família não encontrada"}), 404
    return jsonify(familia)


@api_produtos_bp.put("/api/familias/<int:familia_id>")
def update_familia(familia_id: int):
    data = request.get_json(silent=True) or {}
    nome = (data.get("nome") or "").strip()
    if not nome:
        return jsonify({"error": "Informe o nome da família"}), 400
    if not produto_repo.update_familia(
        familia_id, nome, (data.get("descricao") or "").strip(), data.get("atributos") or []
    ):
        return jsonify({"error": "Família não encontrada"}), 404
    return jsonify({"ok": True})


@api_produtos_bp.delete("/api/familias/<int:familia_id>")
def delete_familia(familia_id: int):
    if produto_repo.count_products(familia_id) > 0:
        return jsonify({"error": "Existem produtos cadastrados nesta família."}), 400
    if not produto_repo.delete_familia(familia_id):
        return jsonify({"error": "Família não encontrada"}), 404
    return jsonify({"ok": True})


# ----------------------------------------------------------------------
# Produtos (cadastro)
# ----------------------------------------------------------------------

@api_produtos_bp.get("/api/produtos-cadastro")
def list_products():
    offset = max(0, request.args.get("offset", 0, type=int))
    limit = min(200, max(1, request.args.get("limit", 60, type=int)))
    items, total = produto_repo.list_products(
        q=(request.args.get("q") or "").strip(),
        familia_id=request.args.get("familia_id", type=int),
        categoria=(request.args.get("categoria") or "").strip(),
        subcategoria=(request.args.get("subcategoria") or "").strip(),
        offset=offset,
        limit=limit,
    )
    for it in items:
        it["imagem_url"] = image_url(it["imagem_filename"])
        it.pop("imagem_filename", None)
    return jsonify({"items": items, "total": total, "offset": offset, "limit": limit})


@api_produtos_bp.post("/api/produtos-cadastro")
def create_product():
    data = request.get_json(silent=True) or {}
    familia_id = data.get("familia_id") or None
    nome = (data.get("nome") or "").strip()
    if not nome:
        return jsonify({"error": "Informe o nome base do produto"}), 400
    produto_id = produto_repo.create_product(
        int(familia_id) if familia_id else None,
        nome,
        (data.get("marca") or "").strip(),
        (data.get("descricao") or "").strip(),
        (data.get("categoria") or "").strip(),
        data.get("variantes") or [],
        (data.get("subcategoria") or "").strip(),
        (data.get("termos_busca") or "").strip(),
        external_id=data.get("external_id"),
    )
    return jsonify({"id": produto_id}), 201


@api_produtos_bp.get("/api/produtos-cadastro/<int:produto_id>")
def get_product(produto_id: int):
    prod = produto_repo.get_product(produto_id)
    if prod is None:
        return jsonify({"error": "Produto não encontrado"}), 404
    return jsonify(_serialize(produto_id, prod))


@api_produtos_bp.put("/api/produtos-cadastro/<int:produto_id>")
def update_product(produto_id: int):
    data = request.get_json(silent=True) or {}
    familia_id = data.get("familia_id") or None
    nome = (data.get("nome") or "").strip()
    if not nome:
        return jsonify({"error": "Informe o nome base do produto"}), 400
    ok, variantes_result = produto_repo.update_product(
        produto_id,
        int(familia_id) if familia_id else None,
        nome,
        (data.get("marca") or "").strip(),
        (data.get("descricao") or "").strip(),
        (data.get("categoria") or "").strip(),
        data.get("variantes") or [],
        (data.get("subcategoria") or "").strip(),
        (data.get("termos_busca") or "").strip(),
        external_id=data.get("external_id"),
    )
    if not ok:
        return jsonify({"error": "Produto não encontrado"}), 404
    return jsonify({"ok": True, "variantes": variantes_result})


@api_produtos_bp.delete("/api/produtos-cadastro/<int:produto_id>")
def delete_product(produto_id: int):
    ok, resultado = produto_repo.delete_product(produto_id)
    if not ok:
        return jsonify({"error": "Produto não encontrado"}), 404
    if not resultado["desativadas"]:
        imagens_service.remover_arquivos_produto(produto_id)
    return jsonify({"ok": True, **resultado})


# ----------------------------------------------------------------------
# Importação por URL
# ----------------------------------------------------------------------

@api_produtos_bp.post("/api/produtos-cadastro/parse-url")
def parse_url():
    data = request.get_json(silent=True) or {}
    url = (data.get("url") or "").strip()
    if not url:
        return jsonify({"error": "Informe a URL do produto"}), 400
    try:
        parsed = parse_url_service.parse_url(url)
    except parse_url_service.ParseError as exc:
        return jsonify({"error": str(exc)}), 422
    except requests.RequestException as exc:
        return jsonify({"error": f"Falha ao acessar a URL: {exc}"}), 502
    return jsonify(parse_url_service.preview(parsed))


@api_produtos_bp.post("/api/produtos-cadastro/from-url")
def create_from_url():
    data = request.get_json(silent=True) or {}
    url = (data.get("url") or "").strip()
    if not url:
        return jsonify({"error": "Informe a URL do produto"}), 400
    try:
        criado = parse_url_service.criar_produto_por_url(url)
    except parse_url_service.ParseError as exc:
        return jsonify({"error": str(exc)}), 422
    except requests.RequestException as exc:
        return jsonify({"error": f"Falha ao acessar a URL: {exc}"}), 502
    return jsonify(criado), 201


# ----------------------------------------------------------------------
# Imagens
# ----------------------------------------------------------------------

@api_produtos_bp.post("/api/produtos-cadastro/<int:produto_id>/imagens")
def upload_imagens(produto_id: int):
    if produto_repo.get_product(produto_id) is None:
        return jsonify({"error": "Produto não encontrado"}), 404
    files = request.files.getlist("files")
    if not files:
        return jsonify({"error": "Nenhum arquivo enviado"}), 400
    saved = imagens_service.salvar_uploads(produto_id, files, produto_repo)
    return jsonify({"imagens": [image_url(str(p)) for p in saved]}), 201


@api_produtos_bp.post("/api/produtos-cadastro/<int:produto_id>/imagens-url")
def baixar_imagens_url(produto_id: int):
    if produto_repo.get_product(produto_id) is None:
        return jsonify({"error": "Produto não encontrado"}), 404
    data = request.get_json(silent=True) or {}
    baixadas, erros = imagens_service.baixar_de_url(
        produto_id, (data.get("url") or "").strip(), produto_repo
    )
    return jsonify({
        "baixadas": [image_url(b["filename"]) for b in baixadas],
        "total": len(baixadas),
        "erros": erros,
    })


@api_produtos_bp.delete("/api/imagens/<int:imagem_id>")
def delete_imagem(imagem_id: int):
    row = produto_repo.delete_imagem(imagem_id)
    if row is None:
        return jsonify({"error": "Imagem não encontrada"}), 404
    imagens_service.remover_arquivo(row["filename"])
    return jsonify({"ok": True})


@api_produtos_bp.post("/api/produtos-cadastro/<int:produto_id>/imagens/capa")
def define_capa(produto_id: int):
    data = request.get_json(silent=True) or {}
    imagem_id = data.get("imagem_id")
    if not imagem_id:
        return jsonify({"error": "Informe a imagem"}), 400
    if not produto_repo.set_imagem_capa(produto_id, int(imagem_id)):
        return jsonify({"error": "Imagem não encontrada no produto"}), 404
    return jsonify({"ok": True})


# ----------------------------------------------------------------------
# Fornecedor x Variante (código, unidade de compra, fator de conversão)
# ----------------------------------------------------------------------

@api_produtos_bp.put("/api/produtos-cadastro/<int:produto_id>/fornecedor-variantes")
def save_fornecedor_variantes(produto_id: int):
    data = request.get_json(silent=True) or {}
    fornecedor_id = data.get("fornecedor_id")
    if not fornecedor_id:
        return jsonify({"error": "Selecione o fornecedor"}), 400
    if produto_repo.get_product(produto_id) is None:
        return jsonify({"error": "Produto não encontrado"}), 404
    with system_conn() as conn:
        produto_repo.save_fornecedor_variantes(
            conn, int(fornecedor_id), produto_id, data.get("itens") or []
        )
        mapping = produto_repo.get_fornecedor_variantes(conn, produto_id)
    return jsonify({"ok": True, "mapping": mapping})


# ----------------------------------------------------------------------
# Categorias e Subcategorias (CRUD)
# ----------------------------------------------------------------------


@api_produtos_bp.get("/api/categorias-tree")
def listar_categorias_tree():
    """Retorna árvore completa de categorias com subcategorias (para o CRUD)."""
    return jsonify(cat_svc.listar())


@api_produtos_bp.post("/api/categorias")
def criar_categoria():
    data = request.get_json(silent=True) or {}
    nome = (data.get("nome") or "").strip()
    if not nome:
        return jsonify({"error": "Informe o nome da categoria"}), 400
    cat_id = cat_svc.criar_categoria(nome)
    if not cat_id:
        return jsonify({"error": "Erro ao criar categoria"}), 400
    return jsonify({"id": cat_id}), 201


@api_produtos_bp.put("/api/categorias/<int:categoria_id>")
def atualizar_categoria(categoria_id: int):
    data = request.get_json(silent=True) or {}
    nome = (data.get("nome") or "").strip()
    if not nome:
        return jsonify({"error": "Informe o nome da categoria"}), 400
    if not cat_svc.atualizar_categoria(categoria_id, nome):
        return jsonify({"error": "Categoria nao encontrada"}), 404
    return jsonify({"ok": True})


@api_produtos_bp.delete("/api/categorias/<int:categoria_id>")
def excluir_categoria(categoria_id: int):
    ok, erro = cat_svc.excluir_categoria(categoria_id)
    if not ok:
        return jsonify({"error": erro}), 400
    return jsonify({"ok": True})


@api_produtos_bp.post("/api/categorias/<int:categoria_id>/subcategorias")
def criar_subcategoria(categoria_id: int):
    data = request.get_json(silent=True) or {}
    nome = (data.get("nome") or "").strip()
    if not nome:
        return jsonify({"error": "Informe o nome da subcategoria"}), 400
    sub_id = cat_svc.criar_subcategoria(categoria_id, nome)
    if not sub_id:
        return jsonify({"error": "Erro ao criar subcategoria"}), 400
    return jsonify({"id": sub_id}), 201


@api_produtos_bp.put("/api/subcategorias/<int:subcategoria_id>")
def atualizar_subcategoria(subcategoria_id: int):
    data = request.get_json(silent=True) or {}
    nome = (data.get("nome") or "").strip()
    if not nome:
        return jsonify({"error": "Informe o nome da subcategoria"}), 400
    if not cat_svc.atualizar_subcategoria(subcategoria_id, nome):
        return jsonify({"error": "Subcategoria nao encontrada"}), 404
    return jsonify({"ok": True})


@api_produtos_bp.delete("/api/subcategorias/<int:subcategoria_id>")
def excluir_subcategoria(subcategoria_id: int):
    ok, erro = cat_svc.excluir_subcategoria(subcategoria_id)
    if not ok:
        return jsonify({"error": erro}), 400
    return jsonify({"ok": True})


# ----------------------------------------------------------------------
# Unidades de compra (CRUD)
# ----------------------------------------------------------------------


@api_produtos_bp.get("/api/unidades-compra")
def listar_unidades_compra():
    apenas_ativas = request.args.get("ativas", "0") == "1"
    return jsonify(unidades_svc.listar(apenas_ativas=apenas_ativas))


@api_produtos_bp.post("/api/unidades-compra")
def criar_unidade_compra():
    data = request.get_json(silent=True) or {}
    unidade_id, erro = unidades_svc.criar(
        data.get("sigla") or "", data.get("descricao") or ""
    )
    if not unidade_id:
        return jsonify({"error": erro or "Erro ao criar unidade"}), 400
    return jsonify({"id": unidade_id}), 201


@api_produtos_bp.put("/api/unidades-compra/<int:unidade_id>")
def atualizar_unidade_compra(unidade_id: int):
    data = request.get_json(silent=True) or {}
    ok, erro = unidades_svc.atualizar(
        unidade_id,
        data.get("sigla") or "",
        data.get("descricao") or "",
        bool(data.get("ativo", True)),
    )
    if not ok:
        return jsonify({"error": erro}), 400
    return jsonify({"ok": True})


@api_produtos_bp.delete("/api/unidades-compra/<int:unidade_id>")
def excluir_unidade_compra(unidade_id: int):
    ok, erro = unidades_svc.excluir(unidade_id)
    if not ok:
        return jsonify({"error": erro}), 400
    return jsonify({"ok": True})


# ----------------------------------------------------------------------
# Produtos por subcategoria + reclassificação
# ----------------------------------------------------------------------


@api_produtos_bp.get("/api/subcategorias/<int:subcategoria_id>/produtos")
def listar_produtos_sub(subcategoria_id: int):
    offset = max(0, request.args.get("offset", 0, type=int))
    limit = min(200, max(1, request.args.get("limit", 60, type=int)))
    items, total = cat_svc.produtos_por_subcategoria(subcategoria_id, offset, limit)
    return jsonify({"items": items, "total": total, "offset": offset, "limit": limit})


@api_produtos_bp.post("/api/produtos/reclassificar")
def reclassificar():
    data = request.get_json(silent=True) or {}
    produto_ids = data.get("produto_ids") or []
    categoria = (data.get("categoria") or "").strip()
    subcategoria = (data.get("subcategoria") or "").strip()
    if not produto_ids:
        return jsonify({"error": "Informe os produtos"}), 400
    if not categoria and not subcategoria:
        return jsonify({"error": "Informe categoria ou subcategoria de destino"}), 400
    count = cat_svc.reclassificar_produtos(produto_ids, categoria, subcategoria)
    return jsonify({"ok": True, "count": count})
