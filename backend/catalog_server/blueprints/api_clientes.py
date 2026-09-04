from __future__ import annotations

from datetime import date

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
from catalog_server.services import credito
from catalog_server.services.documentos import normalizar_e_validar_documento, normalizar_tipo_pessoa
from catalog_server.blueprints.api_usuarios import usuario_id_requisicao

api_clientes_bp = Blueprint("api_clientes", __name__)


def _validar_dados_relacionamento(data: dict) -> None:
    nascimento = data.get("data_nascimento")
    if nascimento not in (None, ""):
        try:
            valor = date.fromisoformat(str(nascimento))
        except ValueError as exc:
            raise ValueError("data_nascimento deve estar no formato AAAA-MM-DD") from exc
        if valor > date.today():
            raise ValueError("data_nascimento não pode estar no futuro")
        data["data_nascimento"] = valor.isoformat()
    else:
        data["data_nascimento"] = None
    canal = str(data.get("canal_preferencial") or "").strip().lower()
    if canal not in {"", "telefone", "whatsapp", "email"}:
        raise ValueError("canal_preferencial inválido")
    data["canal_preferencial"] = canal
    if "consentimento_contato" in data and not isinstance(data["consentimento_contato"], bool):
        raise ValueError("consentimento_contato deve ser booleano")


@api_clientes_bp.get("/api/clientes")
def listar():
    somente_ativos = request.args.get("somente_ativos", "").lower() in ("1", "true")
    vendedor_id = request.args.get("vendedor_id", type=int)
    return jsonify(cliente_repo.list(somente_ativos=somente_ativos, vendedor_id=vendedor_id))


@api_clientes_bp.get("/api/clientes/pagina")
def listar_pagina():
    """Listagem paginada com busca server-side (contrato novo, não quebra o antigo)."""
    q = (request.args.get("q") or "").strip()
    limit = min(max(int(request.args.get("limit", 50) or 50), 1), 200)
    offset = max(int(request.args.get("offset", 0) or 0), 0)
    somente_ativos = request.args.get("somente_ativos", "").lower() in ("1", "true")
    total, itens = cliente_repo.list_page(
        somente_ativos=somente_ativos, termo=q or None, limit=limit, offset=offset,
    )
    return jsonify({"itens": itens, "total": total, "limit": limit, "offset": offset})


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
    s = credito.consultar(cliente_id, total=total)
    if s is None:
        return jsonify({"error": "Cliente não encontrado"}), 404
    return jsonify(s)


@api_clientes_bp.post("/api/clientes")
def criar():
    data = request.get_json(silent=True) or {}
    if not isinstance(data, dict):
        return jsonify({"error": "Payload deve ser um objeto JSON", "code": "payload_invalido"}), 400
    nome = (data.get("nome") or "").strip()
    if not nome:
        return jsonify({"error": "Informe o nome do cliente"}), 400
    try:
        tipo, documento = normalizar_tipo_pessoa(data.get("tipo_pessoa")), data.get("doc")
        documento_normalizado = normalizar_e_validar_documento(documento, tipo)
    except ValueError as exc:
        return jsonify({"error": str(exc), "code": "documento_invalido"}), 400
    data["tipo_pessoa"] = tipo
    data["doc"] = documento_normalizado[1] if documento_normalizado else None
    try:
        _validar_dados_relacionamento(data)
    except ValueError as exc:
        return jsonify({"error": str(exc), "code": "cliente_invalido"}), 400
    if "limite_credito" in data:
        actor = usuario_id_requisicao()
        from catalog_server import permissao
        limite = data.get("limite_credito")
        # O formulário comercial envia zero quando o limite ainda não foi
        # definido. Isso não é uma tentativa de aprovação e não deve bloquear
        # o cadastro feito pelo vendedor.
        if limite not in (None, "", 0, 0.0, "0", "0.00") and not permissao.tem_permissao(actor, "credito", "aprovar"):
            return jsonify({"error": "Limite de crédito é gerenciado pelo Financeiro", "code": "credito_permissao_negada"}), 403
        if limite in (None, "", 0, 0.0, "0", "0.00"):
            data = {k: v for k, v in data.items() if k != "limite_credito"}
    cliente_id = cliente_repo.create(data)
    return jsonify({"id": cliente_id}), 201


@api_clientes_bp.put("/api/clientes/<int:cliente_id>")
def atualizar(cliente_id: int):
    data = request.get_json(silent=True) or {}
    if not isinstance(data, dict):
        return jsonify({"error": "Payload deve ser um objeto JSON", "code": "payload_invalido"}), 400
    if not (data.get("nome") or "").strip():
        return jsonify({"error": "Informe o nome do cliente"}), 400
    try:
        tipo, documento = normalizar_tipo_pessoa(data.get("tipo_pessoa")), data.get("doc")
        documento_normalizado = normalizar_e_validar_documento(documento, tipo)
    except ValueError as exc:
        return jsonify({"error": str(exc), "code": "documento_invalido"}), 400
    data["tipo_pessoa"] = tipo
    data["doc"] = documento_normalizado[1] if documento_normalizado else None
    atual_relacionamento = cliente_repo.get(cliente_id)
    if atual_relacionamento is None:
        return jsonify({"error": "Cliente não encontrado"}), 404
    for campo in ("data_nascimento", "consentimento_contato", "canal_preferencial", "origem_cadastro"):
        if campo not in data:
            data[campo] = atual_relacionamento.get(campo)
    try:
        _validar_dados_relacionamento(data)
    except ValueError as exc:
        return jsonify({"error": str(exc), "code": "cliente_invalido"}), 400
    if "limite_credito" in data:
        actor = usuario_id_requisicao()
        from catalog_server import permissao
        atual = atual_relacionamento
        if atual is None:
            return jsonify({"error": "Cliente não encontrado"}), 404
        if float(data.get("limite_credito") or 0) != float(atual.get("limite_credito") or 0) and not permissao.tem_permissao(actor, "credito", "aprovar"):
            return jsonify({"error": "Limite de crédito é gerenciado pelo Financeiro", "code": "credito_permissao_negada"}), 403
    ok = cliente_repo.update(cliente_id, data)
    if not ok:
        return jsonify({"error": "Cliente não encontrado"}), 404
    return jsonify({"ok": True})


# ── Crediário: aprovação pertence ao Financeiro ────────────

@api_clientes_bp.get("/api/clientes/<int:cliente_id>/credito")
def consultar_credito(cliente_id: int):
    result = credito.consultar(cliente_id)
    if result is None:
        return jsonify({"error": "Cliente não encontrado", "code": "cliente_nao_encontrado"}), 404
    return jsonify(result)


@api_clientes_bp.post("/api/clientes/<int:cliente_id>/credito/solicitar")
def solicitar_credito(cliente_id: int):
    data = request.get_json(silent=True) or {}
    if not isinstance(data, dict):
        return jsonify({"error": "Payload deve ser um objeto JSON", "code": "payload_invalido"}), 400
    actor = usuario_id_requisicao()
    if not actor:
        return jsonify({"error": "Usuário não identificado", "code": "usuario_nao_identificado"}), 401
    try:
        return jsonify(credito.solicitar(cliente_id, data.get("motivo") or "", actor, request.remote_addr, request.headers.get("X-Correlation-ID"))), 201
    except LookupError as exc:
        return jsonify({"error": str(exc), "code": "cliente_nao_encontrado"}), 404
    except PermissionError as exc:
        return jsonify({"error": str(exc), "code": "credito_permissao_negada"}), 403
    except ValueError as exc:
        return jsonify({"error": str(exc), "code": "credito_invalido"}), 400


def _decidir_credito(cliente_id: int, operacao: str):
    data = request.get_json(silent=True) or {}
    if not isinstance(data, dict):
        return jsonify({"error": "Payload deve ser um objeto JSON", "code": "payload_invalido"}), 400
    actor = usuario_id_requisicao()
    if not actor:
        return jsonify({"error": "Usuário não identificado", "code": "usuario_nao_identificado"}), 401
    try:
        if operacao == "aprovar":
            result = credito.aprovar(
                cliente_id, float(data.get("limite_aprovado") or 0), int(data.get("prazo_maximo_dias") or 0),
                data.get("vigencia_inicio") or "", data.get("vigencia_fim") or "", data.get("motivo") or "",
                actor, request.remote_addr, request.headers.get("X-Correlation-ID"), data.get("condicoes_permitidas"),
            )
        elif operacao == "bloquear":
            result = credito.bloquear(cliente_id, data.get("motivo") or "", actor, request.remote_addr, request.headers.get("X-Correlation-ID"))
        else:
            result = credito.suspender(cliente_id, data.get("motivo") or "", actor, request.remote_addr, request.headers.get("X-Correlation-ID"))
        return jsonify(result)
    except LookupError as exc:
        return jsonify({"error": str(exc), "code": "cliente_nao_encontrado"}), 404
    except PermissionError as exc:
        return jsonify({"error": str(exc), "code": "credito_permissao_negada"}), 403
    except (TypeError, ValueError) as exc:
        return jsonify({"error": str(exc), "code": "credito_invalido"}), 400


@api_clientes_bp.post("/api/clientes/<int:cliente_id>/credito/aprovar")
def aprovar_credito(cliente_id: int):
    return _decidir_credito(cliente_id, "aprovar")


@api_clientes_bp.post("/api/clientes/<int:cliente_id>/credito/bloquear")
def bloquear_credito(cliente_id: int):
    return _decidir_credito(cliente_id, "bloquear")


@api_clientes_bp.post("/api/clientes/<int:cliente_id>/credito/suspender")
def suspender_credito(cliente_id: int):
    return _decidir_credito(cliente_id, "suspender")


@api_clientes_bp.post("/api/clientes/<int:cliente_id>/credito/revisar")
def revisar_credito(cliente_id: int):
    data = request.get_json(silent=True) or {}
    if not isinstance(data, dict):
        return jsonify({"error": "Payload deve ser um objeto JSON", "code": "payload_invalido"}), 400
    actor = usuario_id_requisicao()
    if not actor:
        return jsonify({"error": "Usuário não identificado", "code": "usuario_nao_identificado"}), 401
    try:
        return jsonify(credito.revisar(cliente_id, data.get("motivo") or "", actor, request.remote_addr, request.headers.get("X-Correlation-ID")))
    except LookupError as exc:
        return jsonify({"error": str(exc), "code": "cliente_nao_encontrado"}), 404
    except PermissionError as exc:
        return jsonify({"error": str(exc), "code": "credito_permissao_negada"}), 403
    except ValueError as exc:
        return jsonify({"error": str(exc), "code": "credito_invalido"}), 400


@api_clientes_bp.get("/api/clientes/<int:cliente_id>/credito/historico")
def historico_credito(cliente_id: int):
    if credito.consultar(cliente_id) is None:
        return jsonify({"error": "Cliente não encontrado", "code": "cliente_nao_encontrado"}), 404
    return jsonify({"eventos": credito.historico(cliente_id, request.args.get("limite", 100, type=int))})


@api_clientes_bp.get("/api/credito/pendentes")
def pendentes_credito():
    return jsonify({"pendentes": credito.pendentes(request.args.get("limite", 100, type=int))})


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
    from catalog_server.blueprints.api_usuarios import usuario_id_requisicao

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
        usuario_id=usuario_id_requisicao(),
    )
    return jsonify({"id": interacao_id}), 201
