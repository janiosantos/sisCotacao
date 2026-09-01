"""API de pós-venda: interações + garantia (legados) + RMA/troca/crédito (POS-001/002)."""
from __future__ import annotations

from flask import Blueprint, jsonify, request

from catalog_server.repositories import garantia_repo, interacao_repo
from catalog_server.services import posvenda, crm_comissao

api_posvenda_bp = Blueprint("api_posvenda", __name__)


# ─── Interações (legado) ───────────────────────────────────

@api_posvenda_bp.get("/api/posvenda/interacoes")
def listar_interacoes():
    cliente_id = request.args.get("cliente_id", type=int)
    pendentes = request.args.get("pendentes", "").lower() in ("1", "true")
    return jsonify(interacao_repo.list(cliente_id=cliente_id, pendentes=pendentes))


@api_posvenda_bp.post("/api/posvenda/interacoes")
def criar_interacao():
    data = request.get_json(silent=True) or {}
    cliente_nome = (data.get("cliente_nome") or "").strip()
    tipo = (data.get("tipo") or "").strip()
    descricao = (data.get("descricao") or "").strip()
    data_contato = data.get("data_contato")
    if not cliente_nome or not tipo or not data_contato:
        return jsonify({"error": "cliente_nome, tipo e data_contato obrigatórios"}), 400
    if tipo not in ("ligacao", "visita", "email", "whatsapp", "follow_up", "outro"):
        return jsonify({"error": "tipo inválido"}), 400
    interacao_id = interacao_repo.create(
        cliente_id=data.get("cliente_id"),
        cliente_nome=cliente_nome, tipo=tipo, descricao=descricao,
        data_contato=data_contato,
        data_proximo_contato=data.get("data_proximo_contato"),
        orcamento_id=data.get("orcamento_id"),
        usuario_id=data.get("usuario_id"),
    )
    return jsonify({"id": interacao_id}), 201


# ─── Garantia (legado) ─────────────────────────────────────

@api_posvenda_bp.get("/api/posvenda/garantias")
def listar_garantias():
    cliente_id = request.args.get("cliente_id", type=int)
    status = request.args.get("status") or None
    return jsonify(garantia_repo.list(cliente_id=cliente_id, status=status))


@api_posvenda_bp.post("/api/posvenda/garantias")
def criar_garantia():
    data = request.get_json(silent=True) or {}
    cliente_nome = (data.get("cliente_nome") or "").strip()
    produto_nome = (data.get("produto_nome") or "").strip()
    data_inicio = data.get("data_inicio")
    data_fim = data.get("data_fim")
    if not cliente_nome or not produto_nome or not data_inicio or not data_fim:
        return jsonify({"error": "cliente_nome, produto_nome, data_inicio e data_fim obrigatórios"}), 400
    garantia_id = garantia_repo.create(
        cliente_nome, produto_nome, data_inicio, data_fim,
        dias=int(data.get("dias", 90)),
        cliente_id=data.get("cliente_id"),
        orcamento_id=data.get("orcamento_id"),
        produto_id=data.get("produto_id"),
        descricao=data.get("descricao", ""),
        observacao=data.get("observacao", ""),
        data_venda=data.get("data_venda"),
    )
    return jsonify({"id": garantia_id}), 201


@api_posvenda_bp.patch("/api/posvenda/garantias/<int:garantia_id>/status")
def atualizar_status_garantia(garantia_id: int):
    data = request.get_json(silent=True) or {}
    status = (data.get("status") or "").strip()
    if status not in ("ativa", "vencida", "acionada", "cancelada"):
        return jsonify({"error": "status inválido"}), 400
    if not garantia_repo.update_status(garantia_id, status):
        return jsonify({"error": "Garantia não encontrada"}), 404
    return jsonify({"ok": True})


# ─── RMA / troca / crédito (POS-001/002) ───────────────────

@api_posvenda_bp.post("/api/posvenda/rma")
def solicitar_rma():
    data = request.get_json(silent=True) or {}
    try:
        return jsonify(posvenda.solicitar(
            int(data["orcamento_id"]), int(data["produto_id"]), float(data["quantidade"]),
            data.get("motivo") or "", data.get("condicao") or "avariado",
            data.get("lote_id"), data.get("observacao"),
        )), 201
    except LookupError as exc:
        return jsonify({"error": str(exc), "code": "orcamento_nao_encontrado"}), 404
    except (KeyError, ValueError) as exc:
        return jsonify({"error": str(exc), "code": "rma_invalido"}), 400


@api_posvenda_bp.post("/api/posvenda/rma/<int:rma_id>/status")
def transicionar_rma(rma_id: int):
    data = request.get_json(silent=True) or {}
    try:
        return jsonify(posvenda.transicionar(rma_id, data.get("status") or "", data.get("analise")))
    except LookupError as exc:
        return jsonify({"error": str(exc), "code": "rma_nao_encontrado"}), 404
    except ValueError as exc:
        return jsonify({"error": str(exc), "code": "transicao_invalida"}), 400


@api_posvenda_bp.post("/api/posvenda/rma/<int:rma_id>/trocar")
def trocar_rma(rma_id: int):
    data = request.get_json(silent=True) or {}
    try:
        return jsonify(posvenda.trocar(rma_id, int(data["produto_novo_id"]), float(data["quantidade_nova"]), float(data["preco_novo"])))
    except LookupError as exc:
        return jsonify({"error": str(exc), "code": "rma_nao_encontrado"}), 404
    except (KeyError, ValueError) as exc:
        return jsonify({"error": str(exc), "code": "troca_invalida"}), 400


@api_posvenda_bp.get("/api/posvenda/rma")
def listar_rma():
    return jsonify({"rma": posvenda.listar(request.args.get("status"))})


@api_posvenda_bp.get("/api/posvenda/credito/<int:cliente_id>")
def credito_cliente(cliente_id: int):
    return jsonify(posvenda.credito_cliente(cliente_id))


# ─── CRM / oportunidade (POS-004) ──────────────────────────

@api_posvenda_bp.post("/api/posvenda/oportunidades")
def criar_oportunidade():
    data = request.get_json(silent=True) or {}
    try:
        return jsonify(crm_comissao.criar_oportunidade(
            data.get("cliente_id"), data.get("vendedor_id"), data.get("titulo") or "",
            float(data.get("valor") or 0), data.get("etapa") or "prospeccao",
            data.get("proxima_acao"), data.get("proximo_contato"),
        )), 201
    except ValueError as exc:
        return jsonify({"error": str(exc), "code": "oportunidade_invalida"}), 400


@api_posvenda_bp.patch("/api/posvenda/oportunidades/<int:op_id>")
def atualizar_oportunidade(op_id: int):
    data = request.get_json(silent=True) or {}
    try:
        return jsonify(crm_comissao.atualizar_oportunidade(
            op_id, data.get("status") or "", data.get("motivo_perda"), data.get("proxima_acao"),
        ))
    except LookupError as exc:
        return jsonify({"error": str(exc), "code": "oportunidade_nao_encontrada"}), 404
    except ValueError as exc:
        return jsonify({"error": str(exc), "code": "oportunidade_invalida"}), 400


@api_posvenda_bp.get("/api/posvenda/oportunidades")
def listar_oportunidades():
    return jsonify({"oportunidades": crm_comissao.listar_oportunidades(
        request.args.get("vendedor_id", type=int), request.args.get("status"),
    )})


# ─── Comissões (POS-005) ───────────────────────────────────

@api_posvenda_bp.post("/api/posvenda/comissoes/apurar/<int:orcamento_id>")
def apurar_comissao(orcamento_id: int):
    data = request.get_json(silent=True) or {}
    try:
        return jsonify(crm_comissao.apurar_venda(orcamento_id, data.get("vendedor_id")))
    except LookupError as exc:
        return jsonify({"error": str(exc), "code": "orcamento_nao_encontrado"}), 404
    except ValueError as exc:
        return jsonify({"error": str(exc), "code": "comissao_invalida"}), 400


@api_posvenda_bp.post("/api/posvenda/comissoes/reverter/<int:orcamento_id>")
def reverter_comissao(orcamento_id: int):
    return jsonify(crm_comissao.reverter(orcamento_id))


@api_posvenda_bp.get("/api/posvenda/comissoes")
def listar_comissoes():
    return jsonify({"comissoes": crm_comissao.listar_comissoes(request.args.get("status"))})