from __future__ import annotations

from flask import Blueprint, jsonify, request
from catalog_server.repositories import fornecedor_preco_repo, fornecedor_preferencial_repo, solicitacao_repo, tolerancia_repo
from catalog_server.services import custo_engine, cotacao_necessidade, comparacao, alcada_compra, pedido_compra

api_compras_avancado_bp = Blueprint("api_compras_avancado", __name__)


# ─── Custo líquido (Motor Fiscal → Custo) ──────────────────

@api_compras_avancado_bp.get("/api/custos/calcular/<int:produto_id>")
def calcular_custo(produto_id: int):
    fornecedor_id = request.args.get("fornecedor_id", type=int)
    return jsonify(custo_engine.calcular_custo(produto_id, fornecedor_id=fornecedor_id))


@api_compras_avancado_bp.get("/api/fornecedor-preco")
def listar_precos():
    return jsonify(fornecedor_preco_repo.list(
        fornecedor_id=request.args.get("fornecedor_id", type=int),
        produto_id=request.args.get("produto_id", type=int),
    ))


@api_compras_avancado_bp.post("/api/fornecedor-preco")
def upsert_preco():
    data = request.get_json(silent=True) or {}
    f_id = data.get("fornecedor_id")
    v_id = data.get("produto_id")
    preco = data.get("preco")
    if not f_id or not v_id or preco is None:
        return jsonify({"error": "fornecedor_id, produto_id e preco obrigatórios"}), 400
    return jsonify({"id": fornecedor_preco_repo.upsert(
        f_id, v_id, float(preco),
        data.get("prazo_entrega"), float(data.get("icms") or 0), float(data.get("ipi") or 0),
    )}), 201


@api_compras_avancado_bp.get("/api/solicitacoes-compra")
def listar_solicitacoes():
    return jsonify(solicitacao_repo.list(status=request.args.get("status")))


@api_compras_avancado_bp.get("/api/solicitacoes-compra/<int:sc_id>")
def detalhar_solicitacao(sc_id: int):
    sc = solicitacao_repo.get(sc_id)
    if sc is None:
        return jsonify({"error": "Solicitação não encontrada"}), 404
    return jsonify(sc)


@api_compras_avancado_bp.post("/api/solicitacoes-compra")
def criar_solicitacao():
    data = request.get_json(silent=True) or {}
    try:
        sc_id = solicitacao_repo.create(
            data.get("codigo", ""), data.get("descricao", ""),
            data.get("observacao", ""), data.get("usuario_id"),
            data.get("prioridade") or "media", data.get("origem") or "manual",
            data.get("centro_custo"), data.get("deposito_id"),
            data.get("prazo_desejado"),
        )
    except ValueError as exc:
        return jsonify({"error": str(exc), "code": "solicitacao_invalida"}), 400
    return jsonify({"id": sc_id}), 201


@api_compras_avancado_bp.post("/api/solicitacoes-compra/<int:sc_id>/transicao")
def transicionar_solicitacao(sc_id: int):
    data = request.get_json(silent=True) or {}
    status = data.get("status")
    if not status:
        return jsonify({"error": "status é obrigatório", "code": "status_obrigatorio"}), 400
    try:
        return jsonify({"resultado": solicitacao_repo.transicionar(sc_id, status, data.get("usuario_id"))})
    except LookupError as exc:
        return jsonify({"error": str(exc), "code": "solicitacao_nao_encontrada"}), 404
    except ValueError as exc:
        return jsonify({"error": str(exc), "code": "transicao_invalida"}), 400


@api_compras_avancado_bp.post("/api/solicitacoes-compra/<int:sc_id>/itens")
def add_item_solicitacao(sc_id: int):
    data = request.get_json(silent=True) or {}
    v_id = data.get("produto_id")
    qtd = data.get("quantidade")
    if not v_id or not qtd:
        return jsonify({"error": "produto_id e quantidade obrigatórios"}), 400
    try:
        return jsonify({"id": solicitacao_repo.add_item(
            sc_id, v_id, float(qtd), data.get("justificativa", ""),
            data.get("unidade") or "UN", data.get("necessidade"),
            data.get("origem_sugestao"),
        )}), 201
    except ValueError as exc:
        return jsonify({"error": str(exc), "code": "solicitacao_nao_editavel"}), 400


@api_compras_avancado_bp.delete("/api/solicitacoes-compra/<int:sc_id>/itens/<int:item_id>")
def remover_item_solicitacao(sc_id: int, item_id: int):
    try:
        if not solicitacao_repo.remover_item(sc_id, item_id):
            return jsonify({"error": "Item não encontrado", "code": "item_nao_encontrado"}), 404
    except ValueError as exc:
        return jsonify({"error": str(exc), "code": "solicitacao_nao_editavel"}), 400
    return jsonify({"ok": True})


# ─── Cotação a partir de necessidade (COM-008) ─────────────


@api_compras_avancado_bp.post("/api/solicitacoes-compra/<int:sc_id>/cotar")
def cotar_solicitacao(sc_id: int):
    data = request.get_json(silent=True) or {}
    try:
        return jsonify(cotacao_necessidade.gerar_cotacao(sc_id, data.get("apelido"), data.get("usuario_id")))
    except LookupError as exc:
        return jsonify({"error": str(exc), "code": "solicitacao_nao_encontrada"}), 404
    except ValueError as exc:
        return jsonify({"error": str(exc), "code": "solicitacao_nao_cotavel"}), 400


@api_compras_avancado_bp.get("/api/cotacoes/<int:cotacao_id>/propostas")
def propostas_por_produto(cotacao_id: int):
    return jsonify(cotacao_necessidade.buscar_propostas_por_produto(cotacao_id))


# ─── Comparação de propostas (COM-009) ─────────────────────


@api_compras_avancado_bp.get("/api/cotacoes/<int:cotacao_id>/comparacao")
def comparacao_cotacao(cotacao_id: int):
    try:
        return jsonify(comparacao.montar_comparacao(cotacao_id))
    except LookupError as exc:
        return jsonify({"error": str(exc), "code": "cotacao_nao_encontrada"}), 404


@api_compras_avancado_bp.post("/api/cotacoes/precos/<int:preco_id>/vencedor")
def decidir_vencedor(preco_id: int):
    data = request.get_json(silent=True) or {}
    try:
        return jsonify(comparacao.decidir_vencedor(preco_id, data.get("justificativa") or "", data.get("usuario_id")))
    except LookupError as exc:
        return jsonify({"error": str(exc), "code": "proposta_nao_encontrada"}), 404
    except ValueError as exc:
        return jsonify({"error": str(exc), "code": "vencedor_invalido"}), 400


# ─── Alçada de aprovação de compra (COM-010) ───────────────


@api_compras_avancado_bp.get("/api/alcada-compra")
def listar_alcada():
    return jsonify({"regras": alcada_compra.listar_regras()})


@api_compras_avancado_bp.post("/api/alcada-compra")
def criar_alcada():
    data = request.get_json(silent=True) or {}
    try:
        rid = alcada_compra.criar_regra(
            int(data["perfil_id"]) if data.get("perfil_id") else None,
            float(data["limite_valor"]),
            int(data["fornecedor_id"]) if data.get("fornecedor_id") else None,
            data.get("centro_custo"),
            bool(data.get("exige_aprovacao", True)),
        )
    except (KeyError, ValueError, TypeError) as exc:
        return jsonify({"error": str(exc), "code": "alcada_invalida"}), 400
    return jsonify({"id": rid}), 201


@api_compras_avancado_bp.get("/api/alcada-compra/verificar")
def verificar_alcada():
    usuario_id = request.args.get("usuario_id", type=int)
    total = request.args.get("total", type=float)
    if not usuario_id or total is None:
        return jsonify({"error": "usuario_id e total são obrigatórios", "code": "verificacao_invalida"}), 400
    fornecedor_id = request.args.get("fornecedor_id", type=int)
    centro = request.args.get("centro_custo")
    return jsonify({
        "precisa_aprovacao": alcada_compra.precisa_aprovacao(usuario_id, total, fornecedor_id, centro),
        "limite": alcada_compra.limite_usuario(usuario_id, fornecedor_id, centro),
    })


@api_compras_avancado_bp.post("/api/alcada-compra/aprovacoes")
def registrar_aprovacao_api():
    data = request.get_json(silent=True) or {}
    try:
        return jsonify({"aprovacao": alcada_compra.registrar_aprovacao(
            int(data["pedido_id"]), int(data["aprovador_id"]), data["status"],
            data.get("motivo"), data.get("antes"), data.get("depois"),
            int(data.get("versao") or 1),
        )})
    except (KeyError, ValueError) as exc:
        return jsonify({"error": str(exc), "code": "aprovacao_invalida"}), 400


# ─── Pedido de compra (COM-011) e histórico (COM-012) ──────


@api_compras_avancado_bp.post("/api/cotacoes/<int:cotacao_id>/gerar-pedido")
def gerar_pedido_de_cotacao(cotacao_id: int):
    data = request.get_json(silent=True) or {}
    try:
        return jsonify(pedido_compra.gerar_pedido(cotacao_id, data.get("usuario_id")))
    except LookupError as exc:
        return jsonify({"error": str(exc), "code": "cotacao_nao_encontrada"}), 404
    except ValueError as exc:
        return jsonify({"error": str(exc), "code": "pedido_invalido"}), 400


@api_compras_avancado_bp.post("/api/compras/pedidos/<int:pedido_id>/status")
def transicionar_pedido(pedido_id: int):
    data = request.get_json(silent=True) or {}
    status = data.get("status")
    if not status:
        return jsonify({"error": "status é obrigatório", "code": "status_obrigatorio"}), 400
    try:
        return jsonify({"resultado": pedido_compra.transicionar(pedido_id, status, data.get("usuario_id"))})
    except LookupError as exc:
        return jsonify({"error": str(exc), "code": "pedido_nao_encontrado"}), 404
    except ValueError as exc:
        return jsonify({"error": str(exc), "code": "transicao_invalida"}), 400


@api_compras_avancado_bp.post("/api/compras/pedidos/<int:pedido_id>/cancelar")
def cancelar_pedido(pedido_id: int):
    data = request.get_json(silent=True) or {}
    try:
        return jsonify(pedido_compra.cancelar(pedido_id, data.get("motivo")))
    except LookupError as exc:
        return jsonify({"error": str(exc), "code": "pedido_nao_encontrado"}), 404
    except ValueError as exc:
        return jsonify({"error": str(exc), "code": "pedido_nao_cancelavel"}), 400


@api_compras_avancado_bp.get("/api/compras/historico")
def historico_compra():
    produto_id = request.args.get("produto_id", type=int)
    if not produto_id:
        return jsonify({"error": "produto_id é obrigatório", "code": "produto_obrigatorio"}), 400
    return jsonify(pedido_compra.historico_produto(produto_id))


@api_compras_avancado_bp.get("/api/fornecedor-preferencial")
def listar_preferenciais():
    return jsonify(fornecedor_preferencial_repo.list(produto_id=request.args.get("produto_id", type=int)))


@api_compras_avancado_bp.post("/api/fornecedor-preferencial")
def upsert_preferencial():
    data = request.get_json(silent=True) or {}
    v_id = data.get("produto_id")
    f_id = data.get("fornecedor_id")
    if not v_id or not f_id:
        return jsonify({"error": "produto_id e fornecedor_id obrigatórios"}), 400
    return jsonify({"id": fornecedor_preferencial_repo.upsert(
        v_id, f_id, int(data.get("ranking", 1)),
        float(data["ultimo_preco"]) if data.get("ultimo_preco") else None,
        int(data["ultimo_prazo"]) if data.get("ultimo_prazo") else None,
    )}), 201


@api_compras_avancado_bp.get("/api/tolerancias-compra")
def get_tolerancia():
    f_id = request.args.get("fornecedor_id", type=int)
    if not f_id:
        return jsonify({"error": "fornecedor_id obrigatório"}), 400
    t = tolerancia_repo.get(f_id)
    return jsonify(t or {})


@api_compras_avancado_bp.post("/api/tolerancias-compra")
def upsert_tolerancia():
    data = request.get_json(silent=True) or {}
    f_id = data.get("fornecedor_id")
    if not f_id:
        return jsonify({"error": "fornecedor_id obrigatório"}), 400
    return jsonify({"id": tolerancia_repo.upsert(
        f_id, float(data.get("tolerancia_preco_pct", 10)),
        float(data.get("tolerancia_qtd_pct", 10)), data.get("exige_aprovacao", True),
    )}), 201
