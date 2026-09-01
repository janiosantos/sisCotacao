from __future__ import annotations

from flask import Blueprint, jsonify, request

from catalog_server.blueprints.api_usuarios import usuario_id_requisicao
from catalog_server.repositories import preco_historico_repo, promocao_repo, revisao_repo, tabela_preco_repo
from catalog_server.services import pricing_engine, preco_regra as preco_regra_svc

api_precos_bp = Blueprint("api_precos", __name__)


# ─── Simulação de preço (Motor Fiscal → Custo → Precificação) ──

@api_precos_bp.get("/api/precos/calcular/<int:produto_id>")
def calcular_preco(produto_id: int):
    args = request.args
    margem = float(args["margem"]) if args.get("margem") else None
    markup = float(args["markup"]) if args.get("markup") else None
    return jsonify(pricing_engine.calcular_preco(
        produto_id,
        canal=args.get("canal"),
        margem=margem,
        markup=markup,
        comissao=float(args.get("comissao") or 0),
        despesas=float(args.get("despesas") or 0),
        taxas=float(args.get("taxas") or 0),
        tabela_id=args.get("tabela_id", type=int),
        fornecedor_id=args.get("fornecedor_id", type=int),
    ))


@api_precos_bp.get("/api/precos/efetivo/<int:produto_id>")
def preco_efetivo(produto_id: int):
    args = request.args
    return jsonify(pricing_engine.preco_efetivo(
        produto_id,
        canal=args.get("canal") or "varejo",
        cliente_id=args.get("cliente_id", type=int),
        segmento=args.get("segmento"),
        quantidade=args.get("quantidade", type=float),
    ))


# ─── Regras de preço (MDM-007) ─────────────────────────────


@api_precos_bp.get("/api/precos/regras/<int:produto_id>")
def listar_regras_preco(produto_id: int):
    return jsonify({"regras": preco_regra_svc.listar(produto_id)})


@api_precos_bp.post("/api/precos/regras/<int:produto_id>")
def salvar_regra_preco(produto_id: int):
    data = request.get_json(silent=True) or {}
    try:
        regra = preco_regra_svc.salvar(
            produto_id,
            int(data.get("prioridade") or 10),
            data.get("canal"),
            int(data["cliente_id"]) if data.get("cliente_id") else None,
            data.get("segmento"),
            float(data["quantidade_min"]) if data.get("quantidade_min") else None,
            float(data["preco"]) if data.get("preco") is not None else None,
            float(data["desconto_pct"]) if data.get("desconto_pct") is not None else None,
            float(data["margem_minima_pct"]) if data.get("margem_minima_pct") is not None else None,
            data.get("vigencia_inicio"),
            data.get("vigencia_fim"),
            data.get("motivo"),
            usuario_id_requisicao(),
        )
    except ValueError as exc:
        return jsonify({"error": str(exc), "code": "regra_preco_invalida"}), 400
    return jsonify({"regra": regra})


@api_precos_bp.delete("/api/precos/regras/<int:produto_id>/<int:regra_id>")
def excluir_regra_preco(produto_id: int, regra_id: int):
    if not preco_regra_svc.excluir(produto_id, regra_id):
        return jsonify({"error": "Regra não encontrada", "code": "regra_nao_encontrada"}), 404
    return jsonify({"ok": True})


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
    produto_id = data.get("produto_id")
    preco = float(data.get("preco") or 0)
    if not produto_id or preco <= 0:
        return jsonify({"error": "produto_id e preco obrigatórios"}), 400
    tabela_preco_repo.upsert_item(
        tabela_id, produto_id, preco,
        float(data.get("margem")) if data.get("margem") is not None else None,
    )
    return jsonify({"ok": True}), 201


@api_precos_bp.delete("/api/tabelas-preco/<int:tabela_id>/itens")
def remover_item_tabela(tabela_id: int):
    produto_id = request.args.get("produto_id", type=int)
    if not produto_id:
        return jsonify({"error": "produto_id obrigatório"}), 400
    if not tabela_preco_repo.delete_item(tabela_id, produto_id):
        return jsonify({"error": "Item não encontrado"}), 404
    return jsonify({"ok": True})


@api_precos_bp.post("/api/tabelas-preco/<int:tabela_id>/gerar")
def gerar_precos_tabela(tabela_id: int):
    data = request.get_json(silent=True) or {}
    margem = float(data["margem"]) if "margem" in data else None
    markup = float(data["markup"]) if "markup" in data else None
    count = tabela_preco_repo.gerar_precos(tabela_id, margem=margem, markup=markup)
    return jsonify({"gerados": count})


# ─── Reajuste em lote (prévia + aprovação + histórico) ─────

@api_precos_bp.post("/api/tabelas-preco/<int:tabela_id>/previa")
def previa_tabela(tabela_id: int):
    data = request.get_json(silent=True) or {}
    margem = float(data["margem"]) if data.get("margem") is not None else None
    markup = float(data["markup"]) if data.get("markup") is not None else None
    return jsonify(pricing_engine.previa_reajuste(
        tabela_id, margem=margem, markup=markup, termo=data.get("termo"),
    ))


@api_precos_bp.post("/api/tabelas-preco/<int:tabela_id>/reajustar")
def reajustar_tabela(tabela_id: int):
    """Aprova e aplica o reajuste. `confirmado: false` apenas retorna a prévia."""
    data = request.get_json(silent=True) or {}
    margem = float(data["margem"]) if data.get("margem") is not None else None
    markup = float(data["markup"]) if data.get("markup") is not None else None
    confirmado = bool(data.get("confirmado"))
    if not confirmado:
        prev = pricing_engine.previa_reajuste(tabela_id, margem=margem, markup=markup)
        return jsonify({"confirmado": False, **prev})
    result = pricing_engine.aplicar_reajuste(
        tabela_id,
        margem=margem,
        markup=markup,
        usuario_id=usuario_id_requisicao(),
        origem=data.get("origem") or "motor-precificacao",
    )
    return jsonify({"confirmado": True, **result})


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
    produto_id = data.get("produto_id")
    preco = float(data.get("preco_promocional") or 0)
    if not produto_id or preco <= 0:
        return jsonify({"error": "produto_id e preco_promocional obrigatórios"}), 400
    promocao_repo.upsert_item(promocao_id, produto_id, preco)
    return jsonify({"ok": True}), 201


@api_precos_bp.post("/api/promocoes/<int:promocao_id>/aplicar")
def aplicar_promocao(promocao_id: int):
    data = request.get_json(silent=True) or {}
    produto_ids = data.get("produto_ids") or []
    if not produto_ids:
        return jsonify({"error": "Lista de produto_ids vazia"}), 400
    prom = promocao_repo.get(promocao_id)
    if not prom:
        return jsonify({"error": "Promoção não encontrada"}), 404
    count = promocao_repo.aplicar_promocao(promocao_id, produto_ids, prom["tipo"], prom["valor"])
    return jsonify({"aplicados": count})


@api_precos_bp.delete("/api/promocoes/<int:promocao_id>/itens")
def remover_item_promocao(promocao_id: int):
    produto_id = request.args.get("produto_id", type=int)
    if not produto_id:
        return jsonify({"error": "produto_id obrigatório"}), 400
    if not promocao_repo.delete_item(promocao_id, produto_id):
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


# ─── Histórico de preços (auditoria) ───────────────────────

@api_precos_bp.get("/api/precos/historico")
def listar_historico_precos():
    return jsonify(preco_historico_repo.list(
        tabela_id=request.args.get("tabela_id", type=int),
        produto_id=request.args.get("produto_id", type=int),
        termo=request.args.get("q"),
        limit=request.args.get("limit", 200, type=int),
    ))
