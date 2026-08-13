"""API de orçamentos de venda ao cliente (PDV)."""
from __future__ import annotations

from flask import Blueprint, jsonify, request, session
from werkzeug.security import check_password_hash

from catalog_server.blueprints.api_usuarios import SESSION_KEY
from catalog_server.repositories.orcamentos import STATUS_LIST, orcamento_repo, resumo_desconto
from catalog_server.repositories import cliente_repo, usuario_repo
from catalog_server.repositories.pdv_frete import desconto_repo, frete_repo
from catalog_server.repositories.financeiro import contas_repo
from catalog_server.repositories.estoque import estoque_repo
from catalog_server.services import venda_fiscal
from catalog_server.repositories import loja

api_orcamentos_bp = Blueprint("api_orcamentos", __name__)


@api_orcamentos_bp.get("/api/orcamentos")
def listar():
    status = (request.args.get("status") or "").strip()
    somente_meus = request.args.get("somente_meus", "").lower() in ("1", "true")
    usuario_id = session.get(SESSION_KEY) if somente_meus else None
    return jsonify(orcamento_repo.listar(status, usuario_id=usuario_id))


@api_orcamentos_bp.post("/api/orcamentos")
def criar():
    data = request.get_json(silent=True) or {}
    itens = data.get("itens") or []
    if not itens:
        return jsonify({"error": "O orçamento precisa de ao menos 1 item"}), 400
    cliente_nome = data.get("cliente") or ""
    cliente_id = data.get("cliente_id")
    uf_destino = data.get("uf_destino")
    tipo_cliente = data.get("tipo_cliente")
    contribuinte = data.get("contribuinte")
    ie = data.get("ie")
    cliente_doc = None
    if cliente_id:
        cli = cliente_repo.get(cliente_id)
        if cli:
            if not (cliente_nome or "").strip():
                cliente_nome = cli.get("nome") or ""
            cliente_doc = cli.get("doc")
            if not uf_destino:
                uf_destino = cli.get("uf")
            if not tipo_cliente:
                tipo_cliente = "PJ" if cli.get("tipo_pessoa") == "j" else "PF"
            if not contribuinte:
                contribuinte = cli.get("contribuinte")
            if not ie:
                ie = cli.get("ie")
    orcamento_id, numero = orcamento_repo.criar(
        cliente=cliente_nome or "",
        contato=data.get("contato") or "",
        validade_dias=data.get("validade_dias") or 7,
        observacoes=data.get("observacoes") or "",
        desconto=data.get("desconto") or 0,
        itens=itens,
        frete=float(data.get("frete") or 0),
        seguro=float(data.get("seguro") or 0),
        despesas_acessorias=float(data.get("despesas_acessorias") or 0),
        status=data.get("status", "rascunho"),
        condicao_pagamento_id=data.get("condicao_pagamento_id"),
        usuario_id=session.get(SESSION_KEY),
        cliente_id=cliente_id,
        cliente_doc=cliente_doc,
        uf_destino=uf_destino,
        tipo_cliente=tipo_cliente,
        contribuinte=contribuinte,
        ie=ie,
        modelo_documento=data.get("modelo_documento"),
    )
    return jsonify({"id": orcamento_id, "numero": numero}), 201


@api_orcamentos_bp.get("/api/orcamentos/<int:orcamento_id>")
def buscar(orcamento_id: int):
    orcamento = orcamento_repo.buscar(orcamento_id)
    if orcamento is None:
        return jsonify({"error": "Orçamento não encontrado"}), 404
    return jsonify(orcamento)


@api_orcamentos_bp.patch("/api/orcamentos/<int:orcamento_id>")
def atualizar(orcamento_id: int):
    data = request.get_json(silent=True) or {}
    status = data.get("status")
    if status is not None and status not in STATUS_LIST:
        return jsonify({"error": "Status inválido"}), 400

    # Desconto por alçada: para finalizar (faturar) com desconto acima do
    # limite do vendedor, o desconto precisa estar autorizado por um gerente.
    if status == "faturado":
        orc = orcamento_repo.buscar(orcamento_id)
        if orc is None:
            return jsonify({"error": "Orçamento não encontrado"}), 404
        bloqueio = _verificar_alcada(orc)
        if bloqueio is not None:
            return jsonify(bloqueio), 403

        # Estoque: bloqueia venda sem estoque (configurável)
        if loja.bloquear_sem_estoque():
            sem_estoque = []
            for it in orc.get("itens", []):
                qtd = float(it.get("quantidade") or 0)
                vid = it.get("produto_id")
                if vid and qtd > 0:
                    disp = loja.saldo_disponivel(vid)
                    if qtd > disp:
                        sem_estoque.append({"item": it.get("nome"), "disponivel": disp, "solicitado": qtd})
            if sem_estoque:
                return jsonify({"error": "Estoque insuficiente", "code": "sem_estoque",
                                "detalhes": sem_estoque}), 403

        # Snapshot fiscal + validação: grava o FiscalResult por item e bloqueia
        # finalização quando há erro fiscal "hard" (NCM/CFOP/CST/CSOSN).
        snap = venda_fiscal.snapshot_orcamento(orcamento_id)
        if snap and not snap.get("pode_finalizar"):
            return jsonify({
                "error": "Validação fiscal bloqueou a finalização. Corrija os erros abaixo.",
                "code": "fiscal_error",
                "detalhes": snap.get("erros", []),
            }), 403

    if not orcamento_repo.atualizar_cabecalho(
        orcamento_id,
        cliente=data.get("cliente"),
        contato=data.get("contato"),
        validade_dias=data.get("validade_dias"),
        observacoes=data.get("observacoes"),
        status=status,
        desconto=data.get("desconto"),
        condicao_pagamento_id=data.get("condicao_pagamento_id"),
    ):
        return jsonify({"error": "Orçamento não encontrado"}), 404

    # Gatilho: faturar → gerar conta a receber + baixar estoque
    if status == "faturado":
        from datetime import datetime, timedelta
        from catalog_server.db import system_conn as _sc
        orc = orcamento_repo.buscar(orcamento_id)
        if orc:
            venc = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
            try:
                contas_repo.criar_receber(
                    cliente=orc.get("cliente", "") or "",
                    valor=float(orc.get("total") or 0),
                    data_vencimento=venc,
                    descricao=f"Venda {orc.get('numero', '')}",
                    documento=orc.get("numero", ""),
                )
            except Exception:
                pass

            for item in orc.get("itens", []):
                qtd = float(item.get("quantidade") or 0)
                if qtd <= 0:
                    continue
                vid = item.get("variante_id")
                if not vid:
                    pid = item.get("produto_id")
                    if pid:
                        with _sc() as _conn:
                            row = _conn.execute(
                                "SELECT id FROM variantes WHERE produto_id=? AND ativo=1 LIMIT 1",
                                (pid,),
                            ).fetchone()
                            vid = row["id"] if row else None
                if vid:
                    try:
                        estoque_repo.movimentar(
                            deposito_id=1, variante_id=vid,
                            tipo="saida", quantidade=qtd,
                            documento=orc.get("numero", ""),
                        )
                    except Exception:
                        pass

    return jsonify({"ok": True})


@api_orcamentos_bp.put("/api/orcamentos/<int:orcamento_id>/itens")
def substituir_itens(orcamento_id: int):
    data = request.get_json(silent=True) or {}
    itens = data.get("itens") or []
    if not orcamento_repo.substituir_itens(orcamento_id, itens):
        return jsonify({"error": "Orçamento não encontrado"}), 404
    return jsonify({"ok": True})


@api_orcamentos_bp.delete("/api/orcamentos/<int:orcamento_id>")
def excluir(orcamento_id: int):
    if not orcamento_repo.excluir(orcamento_id):
        return jsonify({"error": "Orçamento não encontrado"}), 404
    return jsonify({"ok": True})


# ─── Desconto por alçada ──────────────────────────────────


def _verificar_alcada(orc: dict) -> dict | None:
    """Retorna o payload de bloqueio (403) se o desconto excede a alçada do vendedor."""
    if orc.get("desconto_autorizado"):
        return None
    usuario_id = orc.get("usuario_id")
    if not usuario_id:
        return None
    user = usuario_repo.get(usuario_id)
    if user is None or user.get("perfil") == "admin":
        return None
    limite = float(user.get("desconto_limite_pct") or 0)
    resumo = resumo_desconto(orc)
    if resumo["desconto_pct"] > limite + 1e-9:
        return {
            "error": "Desconto acima da alçada exige autorização de um gerente.",
            "code": "desconto_exige_autorizacao",
            "desconto_pct": resumo["desconto_pct"],
            "limite_pct": limite,
            "desconto_total": resumo["desconto_total"],
        }
    return None


@api_orcamentos_bp.post("/api/orcamentos/<int:orcamento_id>/autorizar-desconto")
def autorizar_desconto(orcamento_id: int):
    """Autoriza o desconto acima da alçada usando credenciais de um gerente.

    Funciona na própria tela do PDV ou remotamente: o gerente informa login e
    senha, e a validação independe da sessão do vendedor.
    """
    data = request.get_json(silent=True) or {}
    login = (data.get("login") or "").strip().lower()
    senha = data.get("senha") or ""
    if not login or not senha:
        return jsonify({"error": "Informe login e senha do gerente"}), 400

    user = usuario_repo.get_by_login(login)
    if not user or not check_password_hash(user["senha_hash"], senha) or not user.get("ativo"):
        return jsonify({"error": "Credenciais inválidas"}), 401
    if user.get("perfil") != "admin" and not user.get("autoriza_desconto"):
        return jsonify({"error": "Usuário não tem permissão para autorizar desconto"}), 403

    orc = orcamento_repo.buscar(orcamento_id)
    if orc is None:
        return jsonify({"error": "Orçamento não encontrado"}), 404
    if orc.get("desconto_autorizado"):
        return jsonify({"ok": True, "ja_autorizado": True, "autorizado_por": orc.get("desconto_autorizado_nome")})

    if not orcamento_repo.autorizar_desconto(orcamento_id, user["id"]):
        return jsonify({"error": "Não foi possível registrar a autorização"}), 500
    return jsonify({"ok": True, "autorizado_por": user["nome"]})


# ─── Políticas ─────────────────────────────────────────────

@api_orcamentos_bp.get("/api/politica-descontos")
def listar_politica_descontos():
    return jsonify(desconto_repo.list())


@api_orcamentos_bp.post("/api/politica-descontos")
def criar_politica_desconto():
    data = request.get_json(silent=True) or {}
    return jsonify({"id": desconto_repo.create(
        data.get("nome", ""), data.get("tipo", "percentual"),
        float(data.get("valor_maximo") or 0),
        float(data.get("valor_minimo") or 0),
        data.get("perfil", ""),
    )}), 201


@api_orcamentos_bp.get("/api/politica-fretes")
def listar_politica_fretes():
    uf = request.args.get("uf") or None
    return jsonify(frete_repo.list(uf=uf))


@api_orcamentos_bp.post("/api/politica-fretes")
def criar_politica_frete():
    data = request.get_json(silent=True) or {}
    return jsonify({"id": frete_repo.create(
        data.get("nome", ""), data.get("uf", ""),
        float(data.get("valor_frete") or 0),
        float(data.get("valor_minimo_pedido") or 0),
        data.get("tipo", "fixo"),
    )}), 201