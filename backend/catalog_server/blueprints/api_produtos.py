"""API do cadastro de produtos (famílias, produtos, variações e imagens)."""
from __future__ import annotations

import requests
from flask import Blueprint, jsonify, request

from catalog_server import categorias as cat_svc, unidades as unidades_svc
from catalog_server.importar_catalogo import importar_json_conteudo
from catalog_server.repositories import (
    produto_repo,
    marcas as marcas_repo,
    grupos as grupos_repo,
    catalog_repo,
)
from catalog_server.services import imagens_service, parse_url_service
from catalog_server.services import imagens_lote
from catalog_server.services import sku_service
from catalog_server.services import unidade_conversao as conv_svc
from catalog_server.services import produto_identificador as ident_svc
from catalog_server.services import cadastro_importacao as cadastro_svc
from catalog_server.services import importacao_planilha
from catalog_server.services import produto_relacao as relacao_svc
from catalog_server.services import galeria_service
from catalog_server.blueprints.api_usuarios import usuario_id_requisicao
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
        nome, (data.get("descricao") or "").strip(), data.get("atributos") or [],
        ncm_padrao=(data.get("ncm_padrao") or "").strip(),
        unidade_padrao=(data.get("unidade_padrao") or "").strip(),
        sku_atributos=[str(x).strip() for x in (data.get("sku_atributos") or []) if str(x).strip()],
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
        familia_id, nome, (data.get("descricao") or "").strip(), data.get("atributos") or [],
        ncm_padrao=(data.get("ncm_padrao") or "").strip(),
        unidade_padrao=(data.get("unidade_padrao") or "").strip(),
        sku_atributos=[str(x).strip() for x in (data.get("sku_atributos") or []) if str(x).strip()],
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
        (data.get("subcategoria") or "").strip(),
        (data.get("termos_busca") or "").strip(),
        external_id=data.get("external_id"),
        grupo_id=int(data["grupo_id"]) if data.get("grupo_id") else None,
        subgrupo_id=int(data["subgrupo_id"]) if data.get("subgrupo_id") else None,
        dados=data.get("dados") or data,
        atributos=data.get("atributos"),
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
    ok, resultado = produto_repo.update_product(
        produto_id,
        int(familia_id) if familia_id else None,
        nome,
        (data.get("marca") or "").strip(),
        (data.get("descricao") or "").strip(),
        (data.get("categoria") or "").strip(),
        (data.get("subcategoria") or "").strip(),
        (data.get("termos_busca") or "").strip(),
        external_id=data.get("external_id"),
        grupo_id=int(data["grupo_id"]) if data.get("grupo_id") else None,
        subgrupo_id=int(data["subgrupo_id"]) if data.get("subgrupo_id") else None,
        dados=data.get("dados") or data,
        atributos=data.get("atributos"),
    )
    if not ok:
        return jsonify({"error": "Produto não encontrado"}), 404
    return jsonify({"ok": True, **resultado})


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
# Importação do catálogo (JSON exportado pelo scraper)
# ----------------------------------------------------------------------

@api_produtos_bp.post("/api/produtos-cadastro/importar-catalogo")
def importar_catalogo():
    """Importa o JSON exportado pelo scraper (upload multipart `file` ou body JSON)."""
    data = request.get_json(silent=True)
    if data is not None:
        try:
            resultado = importar_json_conteudo(request.get_data(as_text=True))
        except (ValueError, TypeError) as exc:
            return jsonify({"error": f"JSON inválido: {exc}"}), 400
        return jsonify({"ok": True, **resultado}), 201

    arquivo = request.files.get("file")
    if arquivo is None:
        return jsonify({"error": "Envie o arquivo JSON no campo 'file' ou um body JSON"}), 400
    try:
        conteudo = arquivo.read().decode("utf-8")
        resultado = importar_json_conteudo(conteudo)
    except (ValueError, TypeError) as exc:
        return jsonify({"error": f"JSON inválido: {exc}"}), 400
    return jsonify({"ok": True, **resultado}), 201


@api_produtos_bp.post("/api/produtos-cadastro/importar-planilha")
def importar_planilha():
    """Importa lista de produtos de um arquivo CSV/XLSX.

    Formato: 1 linha de cabeçalho com DESCRICAO (obrigatória) e colunas
    opcionais MARCA, GRUPO, SUBGRUPO, CATEGORIA, SUBCATEGORIA, FAMILIA.
    Produtos são criados como rascunho (ativo 0).
    """
    arquivo = request.files.get("file")
    if arquivo is None:
        return jsonify({"error": "Envie o arquivo no campo 'file'"}), 400
    nome = arquivo.filename or ""
    if not nome.lower().endswith((".csv", ".xlsx")):
        return jsonify({"error": "Formato não suportado — use .csv ou .xlsx"}), 400
    try:
        resultado = importacao_planilha.importar(
            arquivo.read(), nome, usuario_id=usuario_id_requisicao()
        )
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:  # pragma: no cover
        return jsonify({"error": f"Erro ao importar: {exc}"}), 500
    return jsonify({"ok": True, **resultado}), 201


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


@api_produtos_bp.get("/api/produtos/imagens/galeria/status")
def galeria_status():
    usuario_id = usuario_id_requisicao()
    if usuario_id is None:
        return jsonify({"error": "Sessao nao autenticada"}), 401
    return jsonify(galeria_service.status(usuario_id))


@api_produtos_bp.post("/api/produtos-cadastro/<int:produto_id>/imagens/galeria")
def importar_imagens_galeria(produto_id: int):
    if produto_repo.get_product(produto_id) is None:
        return jsonify({"error": "Produto nao encontrado"}), 404
    data = request.get_json(silent=True) or {}
    values = data.get("image_ids")
    if not isinstance(values, list) or any(
        isinstance(value, bool) or not str(value).isdigit() for value in values
    ):
        return jsonify({"error": "image_ids deve ser uma lista de IDs numericos"}), 400
    try:
        result = galeria_service.importar(
            produto_id, [int(value) for value in values], produto_repo
        )
    except galeria_service.GalleryImageNotFound as exc:
        return jsonify({"error": str(exc)}), 404
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except galeria_service.GalleryUnavailable as exc:
        return jsonify({"error": str(exc)}), 503
    return jsonify(
        {
            "imagens": [image_url(path) for path in result["saved"]],
            "total": len(result["saved"]),
            "deduplicadas": result["deduplicated"],
        }
    ), 201


# ----------------------------------------------------------------------
# Imagens em lote (fornecedor): irmãos, busca no site, preview, aplicar
# ----------------------------------------------------------------------


@api_produtos_bp.get("/api/produtos/<int:produto_id>/irmaos")
def irmaos(produto_id: int):
    """Irmãos do produto (mesmo nome + marca + cor, variando a bitola)."""
    with system_conn() as conn:
        return jsonify(imagens_lote.irmaos(conn, produto_id))


@api_produtos_bp.post("/api/produtos/imagens/buscar-fornecedor")
def buscar_imagens_fornecedor():
    data = request.get_json(silent=True) or {}
    url = (data.get("url") or "").strip()
    if not url:
        return jsonify({"error": "Informe a URL de busca do fornecedor"}), 400
    try:
        return jsonify({"itens": imagens_lote.buscar_fornecedor(url)})
    except Exception as exc:
        return jsonify({"error": f"Não foi possível buscar: {exc}"}), 502


@api_produtos_bp.post("/api/produtos/imagens/preview-fornecedor")
def preview_imagens_fornecedor():
    data = request.get_json(silent=True) or {}
    url = (data.get("url") or "").strip()
    if not url:
        return jsonify({"error": "Informe a URL do produto"}), 400
    try:
        return jsonify({"imagens": imagens_lote.preview_imagens(url)})
    except Exception as exc:
        return jsonify({"error": f"Não foi possível acessar a URL: {exc}"}), 502


@api_produtos_bp.post("/api/produtos/imagens/aplicar-lote")
def aplicar_imagens_lote():
    data = request.get_json(silent=True) or {}
    produto_ids = [int(x) for x in (data.get("produto_ids") or []) if str(x).isdigit()]
    urls = [
        (u.get("url") or "").strip()
        for u in (data.get("imagens") or [])
        if isinstance(u, dict) and (u.get("url") or "").strip()
    ]
    if not produto_ids:
        return jsonify({"error": "Selecione ao menos um produto"}), 400
    if not urls:
        return jsonify({"error": "Selecione ao menos uma imagem"}), 400
    favorita = (data.get("favorita") or "").strip()
    try:
        resultado = imagens_lote.baixar_lote(
            produto_ids, urls, favorita_url=favorita, repo=produto_repo
        )
        return jsonify(resultado)
    except Exception as exc:
        return jsonify({"error": f"Erro ao aplicar: {exc}"}), 500


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


@api_produtos_bp.post("/api/produtos-cadastro/<int:produto_id>/imagens/copiar")
def copiar_imagens(produto_id: int):
    """Copia as imagens de outro produto (duplicação). Preserva ordem/capa."""
    data = request.get_json(silent=True) or {}
    origem_id = data.get("de")
    if not origem_id or not str(origem_id).isdigit():
        return jsonify({"error": "Informe o produto de origem (de)"}), 400
    origem_id = int(origem_id)
    if origem_id == produto_id:
        return jsonify({"error": "Produto de origem e destino são o mesmo"}), 400
    if produto_repo.get_product(produto_id) is None:
        return jsonify({"error": "Produto não encontrado"}), 404
    if produto_repo.get_product(origem_id) is None:
        return jsonify({"error": "Produto de origem não encontrado"}), 404
    copiadas = imagens_service.copiar_imagens(origem_id, produto_id, produto_repo)
    return jsonify({
        "copiadas": len(copiadas),
        "imagens": [image_url(p) for p in copiadas],
    }), 201


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


# ----------------------------------------------------------------------
# Marcas
# ----------------------------------------------------------------------


@api_produtos_bp.get("/api/marcas")
def listar_marcas():
    with system_conn() as conn:
        items = marcas_repo.listar(conn, somente_ativas=request.args.get("ativas") == "1")
    return jsonify(items)


@api_produtos_bp.post("/api/marcas")
def criar_marca():
    data = request.get_json(silent=True) or {}
    nome = (data.get("nome") or "").strip()
    if not nome:
        return jsonify({"error": "Informe o nome da marca"}), 400
    with system_conn() as conn:
        marca = marcas_repo.criar(conn, nome)
    return jsonify(marca), 201


@api_produtos_bp.put("/api/marcas/<int:marca_id>/codigo")
def atualizar_codigo_marca(marca_id: int):
    data = request.get_json(silent=True) or {}
    codigo = (data.get("codigo") or "").strip()
    with system_conn() as conn:
        ok = marcas_repo.atualizar_codigo(conn, marca_id, codigo)
    if not ok:
        return jsonify({"error": "Marca não encontrada"}), 404
    return jsonify({"ok": True})


# ----------------------------------------------------------------------
# Grupos e subgrupos (taxonomia do SKU de acesso rápido)
# ----------------------------------------------------------------------


@api_produtos_bp.get("/api/grupos")
def listar_grupos():
    with system_conn() as conn:
        ativas = request.args.get("ativas") == "1"
        items = grupos_repo.listar_grupos(conn, somente_ativos=ativas)
    return jsonify(items)


@api_produtos_bp.post("/api/grupos")
def criar_grupo():
    data = request.get_json(silent=True) or {}
    codigo = (data.get("codigo") or "").strip()
    nome = (data.get("nome") or "").strip()
    if not codigo or not nome:
        return jsonify({"error": "Informe código e nome do grupo"}), 400
    with system_conn() as conn:
        grupo = grupos_repo.criar_grupo(conn, codigo, nome)
    return jsonify(grupo), 201


@api_produtos_bp.put("/api/grupos/<int:grupo_id>")
def editar_grupo(grupo_id: int):
    data = request.get_json(silent=True) or {}
    codigo = (data.get("codigo") or "").strip()
    nome = (data.get("nome") or "").strip()
    ativo = int(data.get("ativo", 1))
    if not codigo or not nome:
        return jsonify({"error": "Informe código e nome do grupo"}), 400
    with system_conn() as conn:
        ok = grupos_repo.atualizar_grupo(conn, grupo_id, codigo, nome, ativo)
    if not ok:
        return jsonify({"error": "Grupo não encontrado"}), 404
    return jsonify({"ok": True})


@api_produtos_bp.delete("/api/grupos/<int:grupo_id>")
def remover_grupo(grupo_id: int):
    with system_conn() as conn:
        ok, msg = grupos_repo.excluir_grupo(conn, grupo_id)
    if not ok:
        return jsonify({"error": msg}), 400
    return jsonify({"ok": True})


@api_produtos_bp.get("/api/grupos/<int:grupo_id>/subgrupos")
def listar_subgrupos(grupo_id: int):
    with system_conn() as conn:
        ativas = request.args.get("ativas") == "1"
        items = grupos_repo.listar_subgrupos(conn, grupo_id, somente_ativos=ativas)
    return jsonify(items)


@api_produtos_bp.post("/api/grupos/<int:grupo_id>/subgrupos")
def criar_subgrupo(grupo_id: int):
    data = request.get_json(silent=True) or {}
    codigo = (data.get("codigo") or "").strip()
    nome = (data.get("nome") or "").strip()
    if not codigo or not nome:
        return jsonify({"error": "Informe código e nome do subgrupo"}), 400
    with system_conn() as conn:
        sub = grupos_repo.criar_subgrupo(conn, grupo_id, codigo, nome)
    return jsonify(sub), 201


@api_produtos_bp.put("/api/subgrupos/<int:subgrupo_id>")
def editar_subgrupo(subgrupo_id: int):
    data = request.get_json(silent=True) or {}
    codigo = (data.get("codigo") or "").strip()
    nome = (data.get("nome") or "").strip()
    ativo = int(data.get("ativo", 1))
    if not codigo or not nome:
        return jsonify({"error": "Informe código e nome do subgrupo"}), 400
    with system_conn() as conn:
        ok = grupos_repo.atualizar_subgrupo(conn, subgrupo_id, codigo, nome, ativo)
    if not ok:
        return jsonify({"error": "Subgrupo não encontrado"}), 404
    return jsonify({"ok": True})


@api_produtos_bp.delete("/api/subgrupos/<int:subgrupo_id>")
def remover_subgrupo(subgrupo_id: int):
    with system_conn() as conn:
        ok, msg = grupos_repo.excluir_subgrupo(conn, subgrupo_id)
    if not ok:
        return jsonify({"error": msg}), 400
    return jsonify({"ok": True})


# ----------------------------------------------------------------------
# Geração/validação de SKUs (interface de cadastro)
# ----------------------------------------------------------------------


@api_produtos_bp.post("/api/produtos-cadastro/skus/preview")
def preview_skus():
    data = request.get_json(silent=True) or {}
    base = (data.get("base") or "").strip()
    produto_id = int(data.get("produto_id") or 0)
    familia_id = int(data.get("familia_id") or 0)
    itens = data.get("variantes") or []
    grupo_cod = (data.get("grupo_cod") or "").strip()
    subgrupo_cod = (data.get("subgrupo_cod") or "").strip()
    marca_cod = (data.get("marca_cod") or "").strip()
    familia_cod = (data.get("familia_cod") or "").strip()
    if familia_id and not familia_cod:
        familia_cod = sku_service.codigo_familia(familia_id)
    with system_conn() as conn:
        skus = sku_service.gerar_lote(
            base,
            itens,
            produto_id=produto_id,
            conn=conn,
            grupo_cod=grupo_cod or None,
            subgrupo_cod=subgrupo_cod or None,
            marca_cod=marca_cod or None,
            familia_cod=familia_cod or None,
        )
    return jsonify({"skus": skus})


# ----------------------------------------------------------------------
# Conversões de unidade por produto/embalagem (MDM-002)
# ----------------------------------------------------------------------


def _usuario_atual() -> int | None:
    u = getattr(request, "usuario", None)
    return u.get("sub") if u else None


@api_produtos_bp.get("/api/produtos-cadastro/<int:produto_id>/conversoes")
def listar_conversoes(produto_id: int):
    """Conversões ativas do produto (ex.: 1 CX = N UN)."""
    return jsonify({"conversoes": conv_svc.listar(produto_id)})


@api_produtos_bp.post("/api/produtos-cadastro/<int:produto_id>/conversoes")
def salvar_conversao(produto_id: int):
    """Cria/atualiza uma conversão (origem→destino) com unidade base e fator."""
    data = request.get_json(silent=True) or {}
    try:
        c = conv_svc.salvar(
            produto_id,
            data.get("unidade_origem") or "",
            data.get("unidade_destino") or "",
            float(data.get("fator") or 0),
            data.get("unidade_base") or "",
            _usuario_atual(),
        )
    except ValueError as exc:
        return jsonify({"error": str(exc), "code": "conversao_invalida"}), 400
    return jsonify({"conversao": c})


@api_produtos_bp.delete("/api/produtos-cadastro/<int:produto_id>/conversoes/<origem>")
def excluir_conversao(produto_id: int, origem: str):
    if not conv_svc.excluir(produto_id, origem, _usuario_atual()):
        return jsonify({"error": "Conversão não encontrada", "code": "conversao_nao_encontrada"}), 404
    return jsonify({"ok": True})


@api_produtos_bp.get("/api/produtos-cadastro/<int:produto_id>/conversao")
def converter_unidade(produto_id: int):
    """Converte quantidade entre unidades usando as conversões do produto."""
    de = request.args.get("de") or ""
    para = request.args.get("para") or ""
    try:
        qtd = float(request.args.get("qtd") or "1")
    except ValueError:
        return jsonify({"error": "qtd inválida", "code": "quantidade_invalida"}), 400
    try:
        r = conv_svc.converter(produto_id, qtd, de, para)
    except ValueError as exc:
        return jsonify({"error": str(exc), "code": "conversao_invalida"}), 400
    return jsonify(r)


# ----------------------------------------------------------------------
# Identificadores múltiplos por produto (MDM-003)
# ----------------------------------------------------------------------


@api_produtos_bp.get("/api/produtos-cadastro/<int:produto_id>/identificadores")
def listar_identificadores(produto_id: int):
    """Identificadores ativos do produto (EAN/GTIN, códigos interno/fabricante/fornecedor/embalagem)."""
    return jsonify({"identificadores": ident_svc.listar(produto_id)})


@api_produtos_bp.post("/api/produtos-cadastro/<int:produto_id>/identificadores")
def salvar_identificador(produto_id: int):
    data = request.get_json(silent=True) or {}
    try:
        ident = ident_svc.salvar(
            produto_id,
            data.get("tipo") or "",
            data.get("valor") or "",
            data.get("embalagem"),
            data.get("origem"),
            _usuario_atual(),
        )
    except ValueError as exc:
        return jsonify({"error": str(exc), "code": "identificador_invalido"}), 400
    return jsonify({"identificador": ident})


@api_produtos_bp.delete("/api/produtos-cadastro/<int:produto_id>/identificadores/<int:identificador_id>")
def excluir_identificador(produto_id: int, identificador_id: int):
    if not ident_svc.excluir(produto_id, identificador_id):
        return jsonify({"error": "Identificador não encontrado", "code": "identificador_nao_encontrado"}), 404
    return jsonify({"ok": True})


@api_produtos_bp.get("/api/produtos/por-codigo")
def buscar_por_codigo():
    """Busca exata por código (identificador ativo, EAN ou SKU) antes da busca textual."""
    q = request.args.get("q") or ""
    limite = int(request.args.get("limite") or 20)
    return jsonify({"produtos": ident_svc.buscar(q, limite)})


@api_produtos_bp.get("/api/produtos/busca-rapida")
def busca_rapida():
    """Busca rápida do PDV (VEN-002): exata (EAN/SKU/código fornecedor) antes de
    textual, rankeada, com disponibilidade por depósito."""
    q = request.args.get("q") or ""
    limite = int(request.args.get("limite") or 20)
    deposito_id = request.args.get("deposito_id", type=int)
    return jsonify({"produtos": catalog_repo.busca_rapida(q, limite, deposito_id)})


# ----------------------------------------------------------------------
# Workflow de cadastro e importação em lote (MDM-006)
# ----------------------------------------------------------------------


@api_produtos_bp.post("/api/produtos/importar/preview")
def preview_importacao():
    data = request.get_json(silent=True) or {}
    itens = data.get("itens") or []
    if not isinstance(itens, list):
        return jsonify({"error": "itens deve ser uma lista", "code": "importacao_invalida"}), 400
    if len(itens) > 1000:
        return jsonify({"error": "máximo de 1000 linhas por lote", "code": "importacao_limite"}), 400
    return jsonify(cadastro_svc.preview(itens))


@api_produtos_bp.post("/api/produtos/importar")
def importar_produtos():
    data = request.get_json(silent=True) or {}
    itens = data.get("itens") or []
    if not isinstance(itens, list) or not itens:
        return jsonify({"error": "itens deve ser uma lista não vazia", "code": "importacao_invalida"}), 400
    if len(itens) > 1000:
        return jsonify({"error": "máximo de 1000 linhas por lote", "code": "importacao_limite"}), 400
    return jsonify(cadastro_svc.importar(itens, data.get("arquivo_nome"), _usuario_atual()))


@api_produtos_bp.patch("/api/produtos-cadastro/<int:produto_id>/status")
def alterar_status_cadastro(produto_id: int):
    data = request.get_json(silent=True) or {}
    try:
        novo = cadastro_svc.set_status_cadastro(produto_id, data.get("status_cadastro") or "", _usuario_atual())
    except LookupError:
        return jsonify({"error": "Produto não encontrado", "code": "produto_nao_encontrado"}), 404
    except ValueError as exc:
        return jsonify({"error": str(exc), "code": "status_invalido"}), 400
    return jsonify({"ok": True, "status_cadastro": novo})


# ----------------------------------------------------------------------
# Relações entre produtos (MDM-005)
# ----------------------------------------------------------------------


@api_produtos_bp.get("/api/produtos-cadastro/<int:produto_id>/relacoes")
def listar_relacoes(produto_id: int):
    tipo = request.args.get("tipo") or None
    return jsonify({"relacoes": relacao_svc.listar(produto_id, tipo)})


@api_produtos_bp.get("/api/produtos-cadastro/<int:produto_id>/relacoes/relacionados")
def listar_relacionados(produto_id: int):
    """Relações ativas nos dois sentidos (origem e alvo) com nome/sku do outro produto."""
    return jsonify({"relacionados": relacao_svc.relacionados(produto_id)})


@api_produtos_bp.post("/api/produtos-cadastro/<int:produto_id>/relacoes")
def salvar_relacao(produto_id: int):
    data = request.get_json(silent=True) or {}
    try:
        rel = relacao_svc.salvar(
            produto_id,
            int(data.get("relacionado_id") or 0),
            data.get("tipo") or "",
            float(data.get("fator") or 1),
            int(data.get("prioridade") or 1),
            data.get("vigencia_inicio"),
            data.get("vigencia_fim"),
            data.get("motivo"),
            _usuario_atual(),
        )
    except (ValueError, TypeError) as exc:
        return jsonify({"error": str(exc), "code": "relacao_invalida"}), 400
    return jsonify({"relacao": rel})


@api_produtos_bp.delete("/api/produtos-cadastro/<int:produto_id>/relacoes/<int:relacao_id>")
def excluir_relacao(produto_id: int, relacao_id: int):
    if not relacao_svc.excluir(produto_id, relacao_id):
        return jsonify({"error": "Relação não encontrada", "code": "relacao_nao_encontrada"}), 404
    return jsonify({"ok": True})
