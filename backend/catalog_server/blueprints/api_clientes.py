from __future__ import annotations

from flask import Blueprint, jsonify, request

from catalog_server.repositories import (
    cest_repo,
    cfop_repo,
    cliente_repo,
    condicao_repo,
    csosn_repo,
    cst_repo,
    interacao_repo,
    tabela_preco_repo,
    vendedor_repo,
)

api_clientes_bp = Blueprint("api_clientes", __name__)


@api_clientes_bp.get("/api/clientes")
def listar():
    somente_ativos = request.args.get("somente_ativos", "").lower() in ("1", "true")
    vendedor_id = request.args.get("vendedor_id", type=int)
    return jsonify(cliente_repo.list(somente_ativos=somente_ativos, vendedor_id=vendedor_id))


@api_clientes_bp.get("/api/clientes/buscar")
def buscar():
    q = request.args.get("q", "")
    if len(q) < 3:
        return jsonify([])
    return jsonify(cliente_repo.buscar(q))


@api_clientes_bp.get("/api/clientes/<int:cliente_id>")
def detalhar(cliente_id: int):
    cliente = cliente_repo.get(cliente_id)
    if not cliente:
        return jsonify({"error": "Cliente não encontrado"}), 404
    return jsonify(cliente)


@api_clientes_bp.get("/api/clientes/<int:cliente_id>/situacao")
def situacao(cliente_id: int):
    total = request.args.get("total", type=float)
    s = cliente_repo.situacao_credito(cliente_id, total=total)
    if s is None:
        return jsonify({"error": "Cliente não encontrado"}), 404
    return jsonify(s)


@api_clientes_bp.post("/api/clientes")
def criar():
    data = request.get_json(silent=True) or {}
    nome = (data.get("nome") or "").strip()
    if not nome:
        return jsonify({"error": "Informe o nome do cliente"}), 400
    cliente_id = cliente_repo.create(data)
    return jsonify({"id": cliente_id}), 201


@api_clientes_bp.put("/api/clientes/<int:cliente_id>")
def atualizar(cliente_id: int):
    data = request.get_json(silent=True) or {}
    if not (data.get("nome") or "").strip():
        return jsonify({"error": "Informe o nome do cliente"}), 400
    ok = cliente_repo.update(cliente_id, data)
    if not ok:
        return jsonify({"error": "Cliente não encontrado"}), 404
    return jsonify({"ok": True})


@api_clientes_bp.patch("/api/clientes/<int:cliente_id>/ativo")
def alternar_ativo(cliente_id: int):
    ativo = request.args.get("ativo", "").lower() in ("1", "true")
    ok = cliente_repo.set_ativo(cliente_id, ativo)
    if not ok:
        return jsonify({"error": "Cliente não encontrado"}), 404
    return jsonify({"ok": True})


@api_clientes_bp.get("/api/clientes/contexto")
def contexto():
    """Dados auxiliares para o formulário de cliente.

    Reúne vendedores, condições de pagamento, tabelas de preço, tabelas
    fiscais (CFOP/CST/CSOSN/CEST) e listas de segmento/categoria para os
    combos do cadastro — uma única chamada evita N requests no frontend.
    """
    return jsonify({
        "vendedores": vendedor_repo.list(somente_ativos=True),
        "condicoes_pagamento": condicao_repo.list(),
        "tabelas_preco": tabela_preco_repo.list(somente_ativos=True),
        "cfop": cfop_repo.list(),
        "cst_icms": cst_repo.list("cst_icms"),
        "cst_pis": cst_repo.list("cst_pis"),
        "cst_cofins": cst_repo.list("cst_cofins"),
        "csosn": csosn_repo.list(),
        "cest": cest_repo.list(),
        "segmentos": [
            {"valor": "consumidor_final", "label": "Consumidor final"},
            {"valor": "profissional", "label": "Profissional"},
            {"valor": "construtora", "label": "Construtora / incorporadora"},
            {"valor": "revenda", "label": "Revenda / lojista"},
            {"valor": "varejo", "label": "Varejo"},
        ],
        "categorias": [
            {"valor": "pedreiro", "label": "Pedreiro / mestre de obras"},
            {"valor": "eletricista", "label": "Eletricista"},
            {"valor": "encanador", "label": "Encanador / hidráulica"},
            {"valor": "pintor", "label": "Pintor"},
            {"valor": "marceneiro", "label": "Marceneiro"},
            {"valor": "construtora", "label": "Construtora"},
            {"valor": "lojista", "label": "Lojista / revenda"},
            {"valor": "governo", "label": "Órgão público"},
            {"valor": "outro", "label": "Outro"},
        ],
    })


# ── Endereços ──────────────────────────────────────────────

@api_clientes_bp.get("/api/clientes/<int:cliente_id>/enderecos")
def listar_enderecos(cliente_id: int):
    return jsonify(cliente_repo.listar_enderecos(cliente_id))


@api_clientes_bp.post("/api/clientes/<int:cliente_id>/enderecos")
def criar_endereco(cliente_id: int):
    data = request.get_json(silent=True) or {}
    if not data.get("tipo"):
        return jsonify({"error": "tipo obrigatório (cobranca/entrega/faturamento)"}), 400
    end_id = cliente_repo.criar_endereco(cliente_id, data)
    return jsonify({"id": end_id}), 201


@api_clientes_bp.delete("/api/clientes/enderecos/<int:endereco_id>")
def excluir_endereco(endereco_id: int):
    if not cliente_repo.excluir_endereco(endereco_id):
        return jsonify({"error": "Endereço não encontrado"}), 404
    return jsonify({"ok": True})


# ── Contatos ───────────────────────────────────────────────

@api_clientes_bp.get("/api/clientes/<int:cliente_id>/contatos")
def listar_contatos(cliente_id: int):
    return jsonify(cliente_repo.listar_contatos(cliente_id))


@api_clientes_bp.post("/api/clientes/<int:cliente_id>/contatos")
def criar_contato(cliente_id: int):
    data = request.get_json(silent=True) or {}
    if not data.get("nome"):
        return jsonify({"error": "nome do contato obrigatório"}), 400
    ct_id = cliente_repo.criar_contato(cliente_id, data)
    return jsonify({"id": ct_id}), 201


@api_clientes_bp.delete("/api/clientes/contatos/<int:contato_id>")
def excluir_contato(contato_id: int):
    if not cliente_repo.excluir_contato(contato_id):
        return jsonify({"error": "Contato não encontrado"}), 404
    return jsonify({"ok": True})


# ── Apoio Comercial ────────────────────────────────────────

@api_clientes_bp.get("/api/clientes/<int:cliente_id>/apoio-comercial")
def get_apoio_comercial(cliente_id: int):
    apoio = cliente_repo.get_apoio_comercial(cliente_id)
    return jsonify(apoio or {})


@api_clientes_bp.put("/api/clientes/<int:cliente_id>/apoio-comercial")
def upsert_apoio_comercial(cliente_id: int):
    data = request.get_json(silent=True) or {}
    cliente_repo.upsert_apoio_comercial(cliente_id, data)
    return jsonify({"ok": True})


# ── Apoio Fiscal ───────────────────────────────────────────

@api_clientes_bp.get("/api/clientes/<int:cliente_id>/apoio-fiscal")
def get_apoio_fiscal(cliente_id: int):
    apoio = cliente_repo.get_apoio_fiscal(cliente_id)
    return jsonify(apoio or {})


@api_clientes_bp.put("/api/clientes/<int:cliente_id>/apoio-fiscal")
def upsert_apoio_fiscal(cliente_id: int):
    data = request.get_json(silent=True) or {}
    cliente_repo.upsert_apoio_fiscal(cliente_id, data)
    return jsonify({"ok": True})


# ── Interações ──────────────────────────────────────────────

@api_clientes_bp.get("/api/clientes/<int:cliente_id>/interacoes")
def listar_interacoes_cliente(cliente_id: int):
    """Histórico de interações do cliente (ligação/visita/email/whatsapp/follow_up)."""
    return jsonify(interacao_repo.list(cliente_id=cliente_id))


@api_clientes_bp.post("/api/clientes/<int:cliente_id>/interacoes")
def criar_interacao_cliente(cliente_id: int):
    data = request.get_json(silent=True) or {}
    cliente = cliente_repo.get(cliente_id)
    if cliente is None:
        return jsonify({"error": "Cliente não encontrado"}), 404
    tipo = (data.get("tipo") or "").strip()
    descricao = (data.get("descricao") or "").strip()
    data_contato = data.get("data_contato")
    if not tipo or not data_contato:
        return jsonify({"error": "tipo e data_contato obrigatórios"}), 400
    if tipo not in ("ligacao", "visita", "email", "whatsapp", "follow_up", "outro"):
        return jsonify({"error": "tipo inválido"}), 400
    interacao_id = interacao_repo.create(
        cliente_id=cliente_id,
        cliente_nome=cliente["nome"],
        tipo=tipo,
        descricao=descricao,
        data_contato=data_contato,
        data_proximo_contato=data.get("data_proximo_contato"),
        orcamento_id=data.get("orcamento_id"),
        usuario_id=data.get("usuario_id"),
    )
    return jsonify({"id": interacao_id}), 201