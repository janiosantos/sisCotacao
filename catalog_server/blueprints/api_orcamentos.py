"""API de orçamentos de venda ao cliente (PDV)."""
from __future__ import annotations

from flask import Blueprint, jsonify, request, session
from werkzeug.security import check_password_hash

from catalog_server.blueprints.api_usuarios import SESSION_KEY
from catalog_server.repositories.orcamentos import STATUS_LIST, orcamento_repo, resumo_desconto
from catalog_server.repositories import cliente_repo, usuario_repo
from catalog_server.repositories.pdv_frete import desconto_repo, frete_repo
from catalog_server.repositories.financeiro import caixa_repo, contas_repo
from catalog_server.repositories.estoque import estoque_repo
from catalog_server.services import venda_fiscal
from catalog_server.repositories import loja

api_orcamentos_bp = Blueprint("api_orcamentos", __name__)


@api_orcamentos_bp.get("/api/orcamentos")
def listar():
    status = (request.args.get("status") or "").strip()
    somente_meus = request.args.get("somente_meus", "").lower() in ("1", "true")
    usuario_id = session.get(SESSION_KEY) if somente_meus else None
    q = (request.args.get("q") or "").strip()
    data_inicio = request.args.get("data_inicio") or None
    data_fim = request.args.get("data_fim") or None
    return jsonify(orcamento_repo.listar(
        status,
        usuario_id=usuario_id,
        q=q,
        data_inicio=data_inicio,
        data_fim=data_fim,
    ))


@api_orcamentos_bp.post("/api/orcamentos")
def criar():
    data = request.get_json(silent=True) or {}
    itens = data.get("itens") or []
    if not itens:
        return jsonify({"error": "O orçamento precisa de ao menos 1 item"}), 400
    cliente_nome = data.get("cliente") or ""
    cliente_id = data.get("cliente_id")
    # Cliente padrão (id 1) quando o vendedor não informa cliente.
    if not cliente_id and not (cliente_nome or "").strip():
        cliente_id = 1
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


# ─── Recebimento de vendas (caixa) ────────────────────────

FORMAS_PAGAMENTO = ("dinheiro", "pix", "cheque", "cartao_debito", "cartao_credito", "convenio", "boleto", "transferencia")


@api_orcamentos_bp.get("/api/orcamentos/receber/formas")
def formas_pagamento():
    return jsonify(list(FORMAS_PAGAMENTO))


def _normalizar_pagamentos(data: dict) -> tuple[list[tuple[str, float]], str | None]:
    """Normaliza o payload de recebimento (simples ou múltiplas formas).

    Aceita:
      - forma simples: {forma_pagamento, valor_recebido}
      - múltiplas:     {pagamentos: [{forma_pagamento, valor}, ...]}

    Retorna (lista_de_(forma, valor), erro).
    """
    pagamentos_raw = data.get("pagamentos")
    if isinstance(pagamentos_raw, list) and pagamentos_raw:
        out: list[tuple[str, float]] = []
        for p in pagamentos_raw:
            if not isinstance(p, dict):
                continue
            forma = (p.get("forma_pagamento") or "").strip().lower()
            if forma not in FORMAS_PAGAMENTO:
                continue
            try:
                valor = round(float(p.get("valor") or 0), 2)
            except (TypeError, ValueError):
                continue
            if valor > 0:
                out.append((forma, valor))
        if not out:
            return [], "Informe ao menos um pagamento válido"
        return out, None

    forma = (data.get("forma_pagamento") or "dinheiro").strip().lower()
    if forma not in FORMAS_PAGAMENTO:
        return [], "Forma de pagamento inválida"
    try:
        valor = round(float(data.get("valor_recebido") or 0), 2)
    except (TypeError, ValueError):
        return [], "Valor recebido inválido"
    if valor <= 0:
        return [], "Informe o valor recebido"
    return [(forma, valor)], None


@api_orcamentos_bp.post("/api/orcamentos/<int:orcamento_id>/receber")
def receber(orcamento_id: int):
    """Registra o recebimento de uma venda de balcão já faturada (combinável).

    Aceita uma ou mais formas de pagamento simultâneas (ex.: parte em PIX, parte
    em dinheiro). Faz o lançamento no caixa (entrada) para cada forma e baixa a
    conta a receber vinculada pelo número do orçamento. Se o total recebido
    quitar a venda, o status muda para `recebido`.
    """
    data = request.get_json(silent=True) or {}
    pagamentos, erro = _normalizar_pagamentos(data)
    if erro:
        return jsonify({"error": erro}), 400

    orc = orcamento_repo.buscar(orcamento_id)
    if orc is None:
        return jsonify({"error": "Orçamento não encontrado"}), 404
    if orc.get("status") != "faturado":
        return jsonify({"error": "Apenas orçamentos faturados podem ser recebidos"}), 400

    total = round(float(orc.get("total") or 0), 2)
    total_recebido = round(sum(v for _, v in pagamentos), 2)
    troco = round(max(0.0, total_recebido - total), 2)

    # O excedente é devolvido como troco (sempre em dinheiro); subtrai do 1º
    # pagamento em dinheiro antes de lançar no caixa.
    restante_troco = troco
    descricao = f"Venda {orc.get('numero', '')} — {orc.get('cliente', '') or 'cliente'}"
    for forma, valor in pagamentos:
        entrada = valor
        if forma == "dinheiro" and restante_troco > 0:
            abatido = min(entrada, restante_troco)
            entrada = round(entrada - abatido, 2)
            restante_troco = round(restante_troco - abatido, 2)
        if entrada <= 0:
            continue
        try:
            caixa_repo.movimentar(
                "entrada",
                descricao,
                entrada,
                forma_pagamento=forma,
                documento=orc.get("numero", ""),
                orcamento_id=orcamento_id,
                usuario_id=session.get(SESSION_KEY),
            )
        except ValueError as e:
            return jsonify({"error": str(e)}), 400

    entrada_total = round(total_recebido - troco, 2)
    contas_repo.receber_por_documento(orc.get("numero", ""), entrada_total)

    recebido = total_recebido >= total - 1e-9
    if recebido:
        orcamento_repo.atualizar_cabecalho(orcamento_id, status="recebido")

    return jsonify({
        "ok": True,
        "total": total,
        "valor_recebido": total_recebido,
        "troco": troco,
        "recebido": recebido,
    })


@api_orcamentos_bp.post("/api/orcamentos/<int:orcamento_id>/cancelar")
def cancelar(orcamento_id: int):
    """Cancela uma venda de balcão faturada (sem baixa de estoque)."""
    orc = orcamento_repo.buscar(orcamento_id)
    if orc is None:
        return jsonify({"error": "Orçamento não encontrado"}), 404
    if orc.get("status") not in ("faturado", "recebido", "ativo", "liberado", "em_analise"):
        return jsonify({"error": "Orçamento não pode ser cancelado"}), 400
    contas_repo.cancelar_por_documento(orc.get("numero", ""))
    orcamento_repo.atualizar_cabecalho(orcamento_id, status="cancelado")
    return jsonify({"ok": True})


@api_orcamentos_bp.post("/api/orcamentos/<int:orcamento_id>/devolver")
def devolver(orcamento_id: int):
    """Devolve uma venda de balcão: reverte o estoque (entrada) e cancela a venda."""
    orc = orcamento_repo.buscar(orcamento_id)
    if orc is None:
        return jsonify({"error": "Orçamento não encontrado"}), 404
    if orc.get("status") not in ("faturado", "recebido"):
        return jsonify({"error": "Apenas vendas faturadas/recebidas podem ser devolvidas"}), 400

    # Estorno do estoque (entrada) para cada item, invertendo a baixa feita no faturamento.
    devolvidos = 0
    for item in orc.get("itens", []):
        qtd = float(item.get("quantidade") or 0)
        if qtd <= 0:
            continue
        vid = item.get("produto_id") or item.get("variante_id")
        if not vid:
            continue
        try:
            estoque_repo.movimentar(
                deposito_id=1, variante_id=vid,
                tipo="entrada", quantidade=qtd,
                documento=f"DEV {orc.get('numero', '')}",
            )
            devolvidos += 1
        except Exception:
            pass

    contas_repo.cancelar_por_documento(orc.get("numero", ""))
    orcamento_repo.atualizar_cabecalho(orcamento_id, status="cancelado")
    return jsonify({"ok": True, "itens_devolvidos": devolvidos})


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