from __future__ import annotations

from flask import Blueprint, jsonify, request

from catalog_server.repositories import promocao_repo, revisao_repo, tabela_preco_repo

api_precos_bp = Blueprint("api_precos", __name__)


# ─── Tabelas de Preço ──────────────────────────────────────

@api_precos_bp.get("/api/tabelas-preco")
def listar_tabelas():
    somente_ativos = request.args.get("somente_ativos", "").lower() in ("1", "true")
    return jsonify(tabela_preco_repo.list(somente_ativos=somente_ativos))


@api_precos_bp.get("/api/tabelas-preco/<int:tabela_id>")
def detalhar_tabela(tabela_id: int):
    t = tabela_preco_repo.get(tabela_id)
    if not t:
        return jsonify({"error": "Tabela não encontrada"}), 404
    return jsonify(t)


@api_precos_bp.post("/api/tabelas-preco")
def criar_tabela():
    data = request.get_json(silent=True) or {}
    nome = (data.get("nome") or "").strip()
    if not nome:
        return jsonify({"error": "Informe o nome da tabela"}), 400
    tabela_id = tabela_preco_repo.create(
        nome, data.get("tipo", "varejo"),
        float(data.get("margem_padrao") or 0),
        float(data.get("markup") or 0),
    )
    return jsonify({"id": tabela_id}), 201


@api_precos_bp.put("/api/tabelas-preco/<int:tabela_id>")
def atualizar_tabela(tabela_id: int):
    data = request.get_json(silent=True) or {}
    nome = (data.get("nome") or "").strip()
    if not nome:
        return jsonify({"error": "Informe o nome"}), 400
    if not tabela_preco_repo.update(
        tabela_id, nome, data.get("tipo", "varejo"),
        float(data.get("margem_padrao") or 0),
        float(data.get("markup") or 0),
    ):
        return jsonify({"error": "Tabela não encontrada"}), 404
    return jsonify({"ok": True})


@api_precos_bp.patch("/api/tabelas-preco/<int:tabela_id>/ativo")
def alternar_ativo_tabela(tabela_id: int):
    ativo = request.args.get("ativo", "").lower() in ("1", "true")
    if not tabela_preco_repo.set_ativo(tabela_id, ativo):
        return jsonify({"error": "Tabela não encontrada"}), 404
    return jsonify({"ok": True})


@api_precos_bp.get("/api/tabelas-preco/<int:tabela_id>/itens")
def listar_itens_tabela(tabela_id: int):
    q = request.args.get("q", "").strip() or None
    return jsonify(tabela_preco_repo.list_itens(tabela_id, termo=q))


@api_precos_bp.post("/api/tabelas-preco/<int:tabela_id>/itens")
def upsert_item_tabela(tabela_id: int):
    data = request.get_json(silent=True) or {}
    variante_id = data.get("variante_id")
    preco = float(data.get("preco") or 0)
    if not variante_id or preco <= 0:
        return jsonify({"error": "variante_id e preco obrigatórios"}), 400
    tabela_preco_repo.upsert_item(
        tabela_id, variante_id, preco,
        float(data.get("margem")) if data.get("margem") is not None else None,
    )
    return jsonify({"ok": True}), 201


@api_precos_bp.delete("/api/tabelas-preco/<int:tabela_id>/itens")
def remover_item_tabela(tabela_id: int):
    variante_id = request.args.get("variante_id", type=int)
    if not variante_id:
        return jsonify({"error": "variante_id obrigatório"}), 400
    if not tabela_preco_repo.delete_item(tabela_id, variante_id):
        return jsonify({"error": "Item não encontrado"}), 404
    return jsonify({"ok": True})


@api_precos_bp.post("/api/tabelas-preco/<int:tabela_id>/gerar")
def gerar_precos_tabela(tabela_id: int):
    data = request.get_json(silent=True) or {}
    margem = float(data["margem"]) if "margem" in data else None
    markup = float(data["markup"]) if "markup" in data else None
    count = tabela_preco_repo.gerar_precos(tabela_id, margem=margem, markup=markup)
    return jsonify({"gerados": count})


# ─── Promoções ─────────────────────────────────────────────

@api_precos_bp.get("/api/promocoes")
def listar_promocoes():
    ativo = (
        True if request.args.get("ativo", "").lower() in ("1", "true")
        else False if request.args.get("ativo", "").lower() in ("0", "false")
        else None
    )
    return jsonify(promocao_repo.list(ativo=ativo))


@api_precos_bp.get("/api/promocoes/<int:promocao_id>")
def detalhar_promocao(promocao_id: int):
    p = promocao_repo.get(promocao_id)
    if not p:
        return jsonify({"error": "Promoção não encontrada"}), 404
    return jsonify(p)


@api_precos_bp.post("/api/promocoes")
def criar_promocao():
    data = request.get_json(silent=True) or {}
    nome = (data.get("nome") or "").strip()
    if not nome:
        return jsonify({"error": "Informe o nome"}), 400
    tipo = data.get("tipo")
    if tipo not in ("percentual", "valor_fixo"):
        return jsonify({"error": "tipo deve ser percentual ou valor_fixo"}), 400
    promocao_id = promocao_repo.create(
        nome, tipo, float(data.get("valor") or 0),
        data.get("data_inicio"), data.get("data_fim"),
    )
    return jsonify({"id": promocao_id}), 201


@api_precos_bp.put("/api/promocoes/<int:promocao_id>")
def atualizar_promocao(promocao_id: int):
    data = request.get_json(silent=True) or {}
    nome = (data.get("nome") or "").strip()
    if not nome:
        return jsonify({"error": "Informe o nome"}), 400
    if not promocao_repo.update(
        promocao_id, nome, data.get("tipo", "percentual"),
        float(data.get("valor") or 0),
        data.get("data_inicio"), data.get("data_fim"),
        int(data.get("ativo", 1)),
    ):
        return jsonify({"error": "Promoção não encontrada"}), 404
    return jsonify({"ok": True})


@api_precos_bp.get("/api/promocoes/<int:promocao_id>/itens")
def listar_itens_promocao(promocao_id: int):
    q = request.args.get("q", "").strip() or None
    return jsonify(promocao_repo.list_itens(promocao_id, termo=q))


@api_precos_bp.post("/api/promocoes/<int:promocao_id>/itens")
def upsert_item_promocao(promocao_id: int):
    data = request.get_json(silent=True) or {}
    variante_id = data.get("variante_id")
    preco = float(data.get("preco_promocional") or 0)
    if not variante_id or preco <= 0:
        return jsonify({"error": "variante_id e preco_promocional obrigatórios"}), 400
    promocao_repo.upsert_item(promocao_id, variante_id, preco)
    return jsonify({"ok": True}), 201


@api_precos_bp.post("/api/promocoes/<int:promocao_id>/aplicar")
def aplicar_promocao(promocao_id: int):
    data = request.get_json(silent=True) or {}
    variante_ids = data.get("variante_ids") or []
    if not variante_ids:
        return jsonify({"error": "Lista de variante_ids vazia"}), 400
    prom = promocao_repo.get(promocao_id)
    if not prom:
        return jsonify({"error": "Promoção não encontrada"}), 404
    count = promocao_repo.aplicar_promocao(promocao_id, variante_ids, prom["tipo"], prom["valor"])
    return jsonify({"aplicados": count})


@api_precos_bp.delete("/api/promocoes/<int:promocao_id>/itens")
def remover_item_promocao(promocao_id: int):
    variante_id = request.args.get("variante_id", type=int)
    if not variante_id:
        return jsonify({"error": "variante_id obrigatório"}), 400
    if not promocao_repo.delete_item(promocao_id, variante_id):
        return jsonify({"error": "Item não encontrado"}), 404
    return jsonify({"ok": True})


# ─── Revisões ──────────────────────────────────────────────

@api_precos_bp.get("/api/revisoes-preco")
def listar_revisoes():
    tabela_id = request.args.get("tabela_id", type=int)
    return jsonify(revisao_repo.list(tabela_id=tabela_id))


@api_precos_bp.post("/api/revisoes-preco")
def criar_revisao():
    data = request.get_json(silent=True) or {}
    tabela_id = data.get("tabela_id")
    codigo = (data.get("codigo") or "").strip()
    if not tabela_id or not codigo:
        return jsonify({"error": "tabela_id e codigo obrigatórios"}), 400
    rv_id = revisao_repo.create(
        tabela_id, codigo, data.get("descricao", ""),
        data.get("data_validade"), data.get("cliente_id"),
    )
    return jsonify({"id": rv_id}), 201


@api_precos_bp.post("/api/revisoes-preco/<int:rv_id>/fechar")
def fechar_revisao(rv_id: int):
    if not revisao_repo.fechar(rv_id):
        return jsonify({"error": "Revisão não encontrada ou já fechada"}), 404
    return jsonify({"ok": True})


@api_precos_bp.get("/api/tabelas-preco/<int:tabela_id>/itens-margem")
def listar_itens_margem(tabela_id: int):
    q = request.args.get("q", "").strip() or None
    return jsonify(revisao_repo.list_itens_com_margem(tabela_id, termo=q))
