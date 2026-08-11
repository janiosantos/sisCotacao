from __future__ import annotations

from flask import Blueprint, jsonify, request

from catalog_server.repositories import adiantamento_repo, caixa_repo, centro_custo_repo, condicao_repo, contas_repo

api_financeiro_bp = Blueprint("api_financeiro", __name__)


# ─── Caixa ─────────────────────────────────────────────────

@api_financeiro_bp.get("/api/financeiro/caixa/saldo")
def saldo_caixa():
    return jsonify({"saldo": caixa_repo.saldo_atual()})


@api_financeiro_bp.get("/api/financeiro/caixa/movimentos")
def listar_movimentos_caixa():
    limit = request.args.get("limit", 100, type=int)
    tipo = request.args.get("tipo") or None
    return jsonify(caixa_repo.movimentos(limit=limit, tipo=tipo))


@api_financeiro_bp.post("/api/financeiro/caixa/movimento")
def movimentar_caixa():
    data = request.get_json(silent=True) or {}
    tipo = (data.get("tipo") or "").strip()
    if tipo not in ("abertura", "entrada", "saida", "sangria", "suprimento"):
        return jsonify({"error": "tipo inválido"}), 400
    descricao = (data.get("descricao") or "").strip()
    valor = float(data.get("valor") or 0)
    if not descricao or valor <= 0:
        return jsonify({"error": "descricao e valor obrigatórios"}), 400
    result = caixa_repo.movimentar(
        tipo, descricao, valor,
        forma_pagamento=data.get("forma_pagamento", "dinheiro"),
        plano_conta_id=data.get("plano_conta_id"),
        documento=data.get("documento"),
        orcamento_id=data.get("orcamento_id"),
        usuario_id=data.get("usuario_id"),
    )
    return jsonify(result), 201


# ─── Contas a Receber ──────────────────────────────────────

@api_financeiro_bp.get("/api/financeiro/receber")
def listar_receber():
    status = request.args.get("status") or None
    cliente_id = request.args.get("cliente_id", type=int)
    vencimento_ate = request.args.get("vencimento_ate") or None
    return jsonify(contas_repo.listar_receber(status=status, cliente_id=cliente_id, vencimento_ate=vencimento_ate))


@api_financeiro_bp.post("/api/financeiro/receber")
def criar_receber():
    data = request.get_json(silent=True) or {}
    cliente = (data.get("cliente") or "").strip()
    valor = float(data.get("valor") or 0)
    data_vencimento = data.get("data_vencimento")
    if not cliente or valor <= 0 or not data_vencimento:
        return jsonify({"error": "cliente, valor e data_vencimento obrigatórios"}), 400
    conta_id = contas_repo.criar_receber(
        cliente, valor, data_vencimento,
        cliente_id=data.get("cliente_id"),
        descricao=data.get("descricao", ""),
        documento=data.get("documento"),
        plano_conta_id=data.get("plano_conta_id"),
        observacao=data.get("observacao"),
    )
    return jsonify({"id": conta_id}), 201


@api_financeiro_bp.post("/api/financeiro/receber/<int:conta_id>/receber")
def receber_conta(conta_id: int):
    data = request.get_json(silent=True) or {}
    valor = float(data.get("valor") or 0)
    if valor <= 0:
        return jsonify({"error": "valor obrigatório"}), 400
    try:
        result = contas_repo.receber(conta_id, valor, data.get("data_recebimento"))
        return jsonify(result)
    except ValueError as e:
        return jsonify({"error": str(e)}), 404


# ─── Contas a Pagar ────────────────────────────────────────

@api_financeiro_bp.get("/api/financeiro/pagar")
def listar_pagar():
    status = request.args.get("status") or None
    fornecedor_id = request.args.get("fornecedor_id", type=int)
    vencimento_ate = request.args.get("vencimento_ate") or None
    return jsonify(contas_repo.listar_pagar(status=status, fornecedor_id=fornecedor_id, vencimento_ate=vencimento_ate))


@api_financeiro_bp.post("/api/financeiro/pagar")
def criar_pagar():
    data = request.get_json(silent=True) or {}
    fornecedor = (data.get("fornecedor") or "").strip()
    valor = float(data.get("valor") or 0)
    data_vencimento = data.get("data_vencimento")
    if not fornecedor or valor <= 0 or not data_vencimento:
        return jsonify({"error": "fornecedor, valor e data_vencimento obrigatórios"}), 400
    conta_id = contas_repo.criar_pagar(
        fornecedor, valor, data_vencimento,
        fornecedor_id=data.get("fornecedor_id"),
        descricao=data.get("descricao", ""),
        documento=data.get("documento"),
        plano_conta_id=data.get("plano_conta_id"),
        observacao=data.get("observacao"),
    )
    return jsonify({"id": conta_id}), 201


@api_financeiro_bp.post("/api/financeiro/pagar/<int:conta_id>/pagar")
def pagar_conta(conta_id: int):
    data = request.get_json(silent=True) or {}
    valor = float(data.get("valor") or 0)
    if valor <= 0:
        return jsonify({"error": "valor obrigatório"}), 400
    try:
        result = contas_repo.pagar(conta_id, valor, data.get("data_pagamento"))
        return jsonify(result)
    except ValueError as e:
        return jsonify({"error": str(e)}), 404


# ─── Condições de Pagamento ────────────────────────────────

@api_financeiro_bp.get("/api/condicoes-pagamento")
def listar_condicoes():
    return jsonify(condicao_repo.list())


@api_financeiro_bp.get("/api/condicoes-pagamento/<int:c_id>")
def get_condicao(c_id: int):
    c = condicao_repo.get(c_id)
    if not c:
        return jsonify({"error": "Condição não encontrada"}), 404
    return jsonify({**c, "parcelas": condicao_repo.list_parcelas(c_id)})


@api_financeiro_bp.post("/api/condicoes-pagamento")
def criar_condicao():
    data = request.get_json(silent=True) or {}
    nome = (data.get("nome") or "").strip()
    if not nome:
        return jsonify({"error": "Informe o nome"}), 400
    c_id = condicao_repo.create(nome, data.get("descricao", ""))
    return jsonify({"id": c_id}), 201


@api_financeiro_bp.put("/api/condicoes-pagamento/<int:c_id>/parcelas")
def salvar_parcelas(c_id: int):
    data = request.get_json(silent=True) or {}
    parcelas = data.get("parcelas", [])
    condicao_repo.limpar_parcelas(c_id)
    for p in parcelas:
        condicao_repo.upsert_parcela(c_id, p["sequencia"], p["dias"], p["percentual"])
    return jsonify({"ok": True})


# ─── Centros de Custo ──────────────────────────────────────

@api_financeiro_bp.get("/api/centros-custo")
def listar_centros():
    return jsonify(centro_custo_repo.list())


@api_financeiro_bp.post("/api/centros-custo")
def criar_centro():
    data = request.get_json(silent=True) or {}
    codigo = (data.get("codigo") or "").strip()
    nome = (data.get("nome") or "").strip()
    if not codigo or not nome:
        return jsonify({"error": "codigo e nome obrigatórios"}), 400
    return jsonify({"id": centro_custo_repo.create(codigo, nome)}), 201


# ─── Adiantamentos ─────────────────────────────────────────

@api_financeiro_bp.get("/api/adiantamentos")
def listar_adiantamentos():
    tipo = request.args.get("tipo") or None
    return jsonify(adiantamento_repo.list(tipo=tipo))


@api_financeiro_bp.post("/api/adiantamentos")
def criar_adiantamento():
    data = request.get_json(silent=True) or {}
    tipo = data.get("tipo")
    if tipo not in ("cliente", "fornecedor"):
        return jsonify({"error": "tipo deve ser cliente ou fornecedor"}), 400
    return jsonify({"id": adiantamento_repo.create(
        tipo, data.get("pessoa_nome", ""), float(data.get("valor") or 0), data.get("data_adiantamento", ""),
        pessoa_id=data.get("pessoa_id"), observacao=data.get("observacao", ""),
    )}), 201


@api_financeiro_bp.post("/api/adiantamentos/<int:aid>/baixar")
def baixar_adiantamento(aid: int):
    data = request.get_json(silent=True) or {}
    try:
        result = adiantamento_repo.baixar(aid, float(data.get("valor") or 0), data.get("data_baixa", ""))
        return jsonify(result)
    except ValueError as e:
        return jsonify({"error": str(e)}), 404
