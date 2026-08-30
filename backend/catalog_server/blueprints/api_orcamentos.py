"""API de orçamentos de venda ao cliente (PDV)."""
from __future__ import annotations

from flask import Blueprint, jsonify, request, session
from werkzeug.security import check_password_hash

from catalog_server.blueprints.api_usuarios import SESSION_KEY
from catalog_server.repositories.orcamentos import orcamento_repo, resumo_desconto
from catalog_server.orcamento_status import (
    STATUS_LIST,
    aplicar_transicao,
    obter_transicoes,
    pode_editar_conteudo,
    transicao_valida,
)
from catalog_server.repositories import cliente_repo, usuario_repo
from catalog_server.repositories.pdv_frete import desconto_repo, frete_repo
from catalog_server.repositories.financeiro import caixa_repo, contas_repo
from catalog_server.repositories.estoque import estoque_repo
from catalog_server.services import venda_fiscal
from catalog_server.repositories import loja
from catalog_server import contabil_gatilhos
from catalog_server.db import system_conn

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
    # Status "protegidos" (finalizado) só podem ser aplicados pelo PATCH, que
    # passa pelo gate de alçada/estoque/fiscal. Criar já direto como
    # finalizado pulava todas essas checagens — força rascunho aqui, e quem
    # quiser finalizar de fato usa o PATCH depois.
    status_pedido = data.get("status", "rascunho")
    status_criacao = "rascunho" if status_pedido == "finalizado" else status_pedido
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
        status=status_criacao,
        condicao_pagamento_id=data.get("condicao_pagamento_id"),
        usuario_id=getattr(request, "usuario", {}).get("sub") or session.get(SESSION_KEY),
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

    atual = orcamento_repo.buscar(orcamento_id)
    if atual is None:
        return jsonify({"error": "Orçamento não encontrado"}), 404
    status_atual = atual.get("status")

    # Conteúdo (cliente/itens/desconto/condição) — editável só até `liberado`.
    # O repositório levanta PermissionError se o status atual bloquear.
    try:
        orcamento_repo.atualizar_cabecalho(
            orcamento_id,
            cliente=data.get("cliente"),
            contato=data.get("contato"),
            validade_dias=data.get("validade_dias"),
            observacoes=data.get("observacoes"),
            desconto=data.get("desconto"),
            condicao_pagamento_id=data.get("condicao_pagamento_id"),
        )
    except PermissionError as exc:
        return jsonify({"error": str(exc)}), 403

    # Conversão orçamento → pedido (gate de alçada + estoque + fiscal).
    if status == "finalizado":
        if status_atual == "finalizado":
            return jsonify({"error": "Orçamento já finalizado"}), 400
        if not transicao_valida(status_atual, "finalizado"):
            return jsonify({"error": f"Transição {status_atual}→finalizado inválida"}), 400
        orc = orcamento_repo.buscar(orcamento_id)
        if orc is None:
            return jsonify({"error": "Orçamento não encontrado"}), 404
        bloqueio = _verificar_alcada(orc)
        if bloqueio is not None:
            # Persiste o estado "pendente" (aguarda aprovação de gerente).
            from catalog_server.db import system_conn as _sc_pend

            with _sc_pend() as _conn:
                _conn.execute(
                    "UPDATE orcamentos SET desconto_status='pendente' WHERE id=?",
                    (orcamento_id,),
                )
                _conn.commit()
            return jsonify(bloqueio), 403

        # Crédito: bloqueia venda quando o total excede o limite disponível
        # ou quando o cliente tem conta em atraso (configurável). Cliente
        # padrão (CONSUMIDOR, id 1) nunca é bloqueado.
        if orc.get("cliente_id") and orc["cliente_id"] != 1:
            total = float(orc.get("total") or 0)
            situacao = cliente_repo.situacao_credito(orc["cliente_id"], total=total)
            if situacao is not None:
                if loja.bloquear_com_atraso() and situacao.get("excede_por_atraso"):
                    return jsonify({
                        "error": "Cliente possui conta em atraso. Regularize antes de finalizar.",
                        "code": "cliente_atraso",
                        "detalhes": {"saldo_em_atraso": situacao.get("saldo_em_atraso")},
                    }), 403
                if loja.bloquear_sem_credito() and situacao.get("excede_limite"):
                    return jsonify({
                        "error": "Venda acima do limite de crédito disponível.",
                        "code": "sem_credito",
                        "detalhes": {
                            "limite_credito": situacao.get("limite_credito"),
                            "limite_utilizado": situacao.get("limite_utilizado"),
                            "limite_disponivel": situacao.get("limite_disponivel"),
                            "total": total,
                        },
                    }), 403

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
        # finalização quando há erro fiscal "hard" (NCM/CFOP/CST/CSOSN) — só
        # quando a loja está configurada para isso (bloquear_venda_sem_fiscal).
        snap = venda_fiscal.snapshot_orcamento(orcamento_id)
        if loja.bloquear_sem_fiscal() and snap and not snap.get("pode_finalizar"):
            return jsonify({
                "error": "Validação fiscal bloqueou a finalização. Corrija os erros abaixo.",
                "code": "fiscal_error",
                "detalhes": snap.get("erros", []),
            }), 403

    # Demais transições de status (rascunho/ativo/em_analise/liberado,
    # cancelado; e reabrir finalizado→liberado exige permissão).
    elif status is not None and status != status_atual:
        if status == "liberado" and status_atual == "finalizado":
            from catalog_server import permissao

            payload = getattr(request, "usuario", None)
            if not payload or not permissao.tem_permissao(payload.get("sub"), "orcamentos", "aprovar"):
                return jsonify({"error": "Reabrir pedido exige permissão de aprovação"}), 403
        if not transicao_valida(status_atual, status):
            return jsonify({"error": f"Transição {status_atual}→{status} inválida"}), 400
        if not aplicar_transicao(orcamento_id, status):
            return jsonify({"error": "Não foi possível aplicar a transição"}), 400

    # Finalização e seus efeitos financeiros/estoque precisam compartilhar a
    # mesma transação. Nenhum efeito parcial pode deixar o pedido finalizado.
    if status == "finalizado":
        from datetime import datetime, timedelta
        from catalog_server.services.parcelas_venda import gerar_contas_receber

        try:
            with system_conn() as conn:
                estado = conn.execute(
                    "SELECT status FROM orcamentos WHERE id=? FOR UPDATE",
                    (orcamento_id,),
                ).fetchone()
                if not estado or not transicao_valida(estado["status"], "finalizado"):
                    return jsonify({"error": "Transição finalizado inválida"}), 409

                orc = orcamento_repo.buscar(orcamento_id, _conn=conn)
                if not orc:
                    return jsonify({"error": "Orçamento não encontrado"}), 404

                # A prazo gera parcelas; à vista/balcão mantém uma conta única.
                parcelas = gerar_contas_receber(orc, _conn=conn)
                if not parcelas:
                    venc = (datetime.now() + timedelta(days=0)).strftime("%Y-%m-%d")
                    contas_repo.criar_receber(
                        cliente=orc.get("cliente", "") or "",
                        cliente_id=orc.get("cliente_id"),
                        valor=float(orc.get("total") or 0),
                        data_vencimento=venc,
                        descricao=f"Venda {orc.get('numero', '')}",
                        documento=orc.get("numero", ""),
                        _conn=conn,
                    )

                for item in orc.get("itens", []):
                    qtd = float(item.get("quantidade") or 0)
                    if qtd <= 0:
                        continue
                    vid = item.get("produto_id") or item.get("variante_id")
                    if not vid:
                        raise ValueError("item sem produto")
                    if loja.bloquear_sem_estoque():
                        estoque_repo.movimentar_fato(
                            deposito_id=1,
                            variante_id=vid,
                            tipo="saida",
                            quantidade=qtd,
                            idempotency_key=f"venda:{orcamento_id}:item:{item.get('id') or vid}",
                            origem_tipo="venda",
                            origem_id=orcamento_id,
                            documento=orc.get("numero", ""),
                            _conn=conn,
                        )
                    else:
                        # Compatibilidade com a configuração legada que permite
                        # venda sem saldo: ainda registra a baixa na transação.
                        estoque_repo.movimentar(
                            deposito_id=1,
                            variante_id=vid,
                            tipo="saida",
                            quantidade=qtd,
                            documento=orc.get("numero", ""),
                            _conn=conn,
                        )

                contabil_gatilhos.disparar(
                    "venda_autorizada",
                    evento_id=orcamento_id,
                    valor=float(orc.get("total") or 0),
                    historico=f"Venda {orc.get('numero', '')} — {orc.get('cliente', '') or 'cliente'}",
                    periodo_competencia=datetime.now().strftime("%Y-%m"),
                    origem_tipo="orcamento",
                    _conn=conn,
                )
                if not aplicar_transicao(orcamento_id, "finalizado", _conn=conn):
                    return jsonify({"error": "Transição finalizado inválida"}), 409
        except ValueError as exc:
            return jsonify({"error": str(exc), "code": "operacao_invalida"}), 409

    return jsonify({"ok": True})


@api_orcamentos_bp.post("/api/orcamentos/<int:orcamento_id>/reabrir")
def reabrir(orcamento_id: int):
    """Reabre um pedido finalizado para correção (exige permissão de aprovação).

    Volta para `liberado` (ou `em_analise` se ainda não estava liberado),
    desfaz a marcação de pedido e revoga a autorização de desconto — qualquer
    desconto acima da alçada volta a `pendente`, exigindo nova autorização.

    Pedido finalizado com boleto emitido nunca pode ser alterado/reaberto.
    """
    orc = orcamento_repo.buscar(orcamento_id)
    if orc is None:
        return jsonify({"error": "Orçamento não encontrado"}), 404
    if orc.get("status") not in ("finalizado",):
        return jsonify({"error": "Apenas pedidos finalizados podem ser reabertos"}), 400

    from catalog_server.services.boletos import tem_boleto_emitido

    if tem_boleto_emitido(orc.get("numero") or ""):
        return jsonify({"error": "Pedido com boleto emitido não pode ser alterado/reaberto"}), 403

    from catalog_server import permissao

    payload = getattr(request, "usuario", None)
    usuario_id = payload.get("sub") if payload else None
    aprova = usuario_id and (
        (usuario_repo.get(usuario_id) or {}).get("autoriza_desconto")
        or permissao.tem_permissao(usuario_id, "orcamentos", "aprovar")
    )
    if not aprova:
        return jsonify({"error": "Reabrir pedido exige permissão de aprovação"}), 403

    # Reabertura, estorno financeiro e reversão do estoque formam uma única
    # transação. Só reversões originadas pelo novo fluxo são automatizadas;
    # movimentos legados exigem conciliação explícita.
    from catalog_server.services.parcelas_venda import estornar_contas_receber

    try:
        with system_conn() as conn:
            estado = conn.execute(
                "SELECT status FROM orcamentos WHERE id=? FOR UPDATE",
                (orcamento_id,),
            ).fetchone()
            if not estado or estado["status"] != "finalizado":
                return jsonify({"error": "Pedido já foi alterado por outra operação"}), 409

            movimentos = conn.execute(
                "SELECT deposito_id, produto_id, quantidade, id FROM estoque_movimento"
                " WHERE origem_tipo='venda' AND origem_id=? AND tipo='saida' FOR UPDATE",
                (orcamento_id,),
            ).fetchall()
            for movimento in movimentos:
                estoque_repo.movimentar_fato(
                    deposito_id=movimento["deposito_id"],
                    variante_id=movimento["produto_id"],
                    tipo="entrada",
                    quantidade=float(movimento["quantidade"] or 0),
                    idempotency_key=f"reabertura:{orcamento_id}:movimento:{movimento['id']}",
                    origem_tipo="reabertura",
                    origem_id=orcamento_id,
                    documento=orc.get("numero", ""),
                    observacao=f"Estorno da movimentação {movimento['id']}",
                    _conn=conn,
                )

            estornar_contas_receber(orc, _conn=conn)
            if not aplicar_transicao(orcamento_id, "liberado", _conn=conn):
                return jsonify({"error": "Não foi possível reabrir o pedido"}), 409
            # Revoga a autorização de desconto: correção exige reavaliação.
            orcamento_repo._revogar_aprovacao(conn, orcamento_id, "pedido reaberto para correção")
    except ValueError as exc:
        return jsonify({"error": str(exc), "code": "operacao_invalida"}), 409
    return jsonify({"ok": True})


@api_orcamentos_bp.put("/api/orcamentos/<int:orcamento_id>/itens")
def substituir_itens(orcamento_id: int):
    data = request.get_json(silent=True) or {}
    itens = data.get("itens") or []
    try:
        if not orcamento_repo.substituir_itens(orcamento_id, itens):
            return jsonify({"error": "Orçamento não encontrado"}), 404
    except PermissionError as exc:
        return jsonify({"error": str(exc)}), 403
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


def _normalizar_pagamentos(data: dict) -> tuple[list[tuple[str, float, str | None, str | None]], str | None]:
    """Normaliza o payload de recebimento (simples ou múltiplas formas).

    Aceita:
      - forma simples: {forma_pagamento, valor_recebido, bandeira?, codigo_autorizacao?}
      - múltiplas:     {pagamentos: [{forma_pagamento, valor, bandeira?, codigo_autorizacao?}, ...]}

    Retorna (lista_de_(forma, valor, bandeira, codigo_autorizacao), erro).
    """
    pagamentos_raw = data.get("pagamentos")
    if isinstance(pagamentos_raw, list) and pagamentos_raw:
        out: list[tuple[str, float, str | None, str | None]] = []
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
                bandeira = (p.get("bandeira") or "").strip() or None
                codigo = (p.get("codigo_autorizacao") or "").strip() or None
                out.append((forma, valor, bandeira, codigo))
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
    bandeira = (data.get("bandeira") or "").strip() or None
    codigo = (data.get("codigo_autorizacao") or "").strip() or None
    return [(forma, valor, bandeira, codigo)], None


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
    if orc.get("status") != "finalizado":
        return jsonify({"error": "Apenas pedidos finalizados podem ser recebidos"}), 400

    total = round(float(orc.get("total") or 0), 2)
    total_recebido = round(sum(v for _, v, _, _ in pagamentos), 2)
    troco = round(max(0.0, total_recebido - total), 2)

    # O excedente é devolvido como troco (sempre em dinheiro); subtrai do 1º
    # pagamento em dinheiro antes de lançar no caixa.
    restante_troco = troco
    descricao = f"Venda {orc.get('numero', '')} — {orc.get('cliente', '') or 'cliente'}"
    for forma, valor, bandeira, codigo in pagamentos:
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
                usuario_id=getattr(request, "usuario", {}).get("sub") or session.get(SESSION_KEY),
                bandeira=bandeira,
                codigo_autorizacao=codigo,
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


# ─── Boleto de venda a prazo ───────────────────────────────

@api_orcamentos_bp.post("/api/orcamentos/<int:orcamento_id>/boleto")
def gerar_boleto(orcamento_id: int):
    """Gera boletos das parcelas de uma venda a prazo (pedido finalizado)."""
    from catalog_server.services.boletos import gerar_boletos_parcelas

    orc = orcamento_repo.buscar(orcamento_id)
    if orc is None:
        return jsonify({"error": "Orçamento não encontrado"}), 404
    if orc.get("status") not in ("finalizado", "recebido"):
        return jsonify({"error": "Apenas pedidos finalizados/recebidos podem gerar boleto"}), 400
    boletos = gerar_boletos_parcelas(orc.get("numero") or "")
    if not boletos:
        return jsonify({"error": "Venda sem parcelas (à vista) — nenhum boleto gerado"}), 400
    return jsonify({"ok": True, "boletos": boletos})


@api_orcamentos_bp.post("/api/orcamentos/<int:orcamento_id>/cancelar")
def cancelar(orcamento_id: int):
    """Cancela uma venda de balcão faturada (sem baixa de estoque)."""
    orc = orcamento_repo.buscar(orcamento_id)
    if orc is None:
        return jsonify({"error": "Orçamento não encontrado"}), 404
    if orc.get("status") not in ("finalizado", "recebido", "ativo", "liberado", "em_analise"):
        return jsonify({"error": "Orçamento não pode ser cancelado"}), 400
    contas_repo.cancelar_por_documento(orc.get("numero", ""))
    aplicar_transicao(orcamento_id, "cancelado")
    return jsonify({"ok": True})


@api_orcamentos_bp.post("/api/orcamentos/<int:orcamento_id>/devolver")
def devolver(orcamento_id: int):
    """Devolve uma venda de balcão: reverte o estoque (entrada) e cancela a venda."""
    orc = orcamento_repo.buscar(orcamento_id)
    if orc is None:
        return jsonify({"error": "Orçamento não encontrado"}), 404
    if orc.get("status") not in ("finalizado", "recebido"):
        return jsonify({"error": "Apenas pedidos finalizados/recebidos podem ser devolvidos"}), 400

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
    aplicar_transicao(orcamento_id, "devolvido")
    return jsonify({"ok": True, "itens_devolvidos": devolvidos})


# ─── Desconto por alçada ──────────────────────────────────


def _verificar_alcada(orc: dict) -> dict | None:
    """Retorna o payload de bloqueio (403) se o desconto excede a alçada do vendedor.

    Sem vendedor identificado (sessão ausente/expirada) ou usuário
    inexistente, a alçada é 0% — qualquer desconto exige autorização — em
    vez de pular a checagem. Pular era um jeito fácil de burlar o limite
    (bastava não estar logado).

    Desconto dentro da alçada nunca pede autorização (status permanece `ok`).
    """
    if orc.get("desconto_status") in ("aprovado",):
        return None
    if orc.get("desconto_autorizado"):
        return None
    usuario_id = orc.get("usuario_id")
    user = usuario_repo.get(usuario_id) if usuario_id else None
    limite = float(user.get("desconto_limite_pct") or 0) if user is not None else 0.0
    resumo = resumo_desconto(orc)
    # Sem desconto efetivo (ou irrelevante), não há o que autorizar. O epsilon
    # em centavos evita que uma diferença de arredondamento (subtotal × base)
    # vire um "desconto" minúsculo que, com alçada 0%, dispararia o bloqueio.
    if resumo["desconto_total"] <= 0.01:
        return None
    if resumo["desconto_pct"] > limite + 1e-6:
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

    Segregação (TOTVS): o aprovador deve ser OUTRO usuário (não o vendedor do
    orçamento), ter `autoriza_desconto` ou a permissão RBAC `orcamentos.aprovar`
    e alçada (`desconto_limite_pct`) ≥ desconto solicitado. Registra log.
    """
    data = request.get_json(silent=True) or {}
    login = (data.get("login") or "").strip().lower()
    senha = data.get("senha") or ""
    if not login or not senha:
        return jsonify({"error": "Informe login e senha do gerente"}), 400

    user = usuario_repo.get_by_login(login)
    if not user or not check_password_hash(user["senha_hash"], senha) or not user.get("ativo"):
        return jsonify({"error": "Credenciais inválidas"}), 401
    # Autoriza desconto: flag autoriza_desconto (legado) ou a permissão RBAC
    # `orcamentos.aprovar` (admin cobre via superuser — migração 0075/0077).
    from catalog_server import permissao

    pode_aprovar = user.get("autoriza_desconto") or permissao.tem_permissao(user["id"], "orcamentos", "aprovar")
    if not pode_aprovar:
        return jsonify({"error": "Usuário não tem permissão para autorizar desconto"}), 403

    orc = orcamento_repo.buscar(orcamento_id)
    if orc is None:
        return jsonify({"error": "Orçamento não encontrado"}), 404
    if orc.get("desconto_autorizado") or orc.get("desconto_status") == "aprovado":
        return jsonify({"ok": True, "ja_autorizado": True, "autorizado_por": orc.get("desconto_autorizado_nome")})

    # Segregação: aprovador não pode ser o próprio vendedor do orçamento.
    if orc.get("usuario_id") and orc["usuario_id"] == user["id"]:
        return jsonify({"error": "O vendedor não pode autorizar o próprio desconto"}), 403

    # Alçada do aprovador deve cobrir o desconto solicitado (superuser aprova tudo).
    resumo = resumo_desconto(orc)
    desconto_pct = float(resumo.get("desconto_pct") or 0)
    limite_aprovador = float(user.get("desconto_limite_pct") or 0)
    from catalog_server.db import system_conn as _sc_su

    with _sc_su() as _conn:
        eh_superuser = _conn.execute(
            "SELECT 1 FROM usuario_perfis up JOIN perfis p ON p.id=up.perfil_id"
            " WHERE up.usuario_id=? AND p.nome='Administrador'",
            (user["id"],),
        ).fetchone() is not None
    if not eh_superuser and desconto_pct > limite_aprovador + 1e-6:
        return jsonify({
            "error": "A alçada do aprovador não cobre o desconto solicitado.",
            "desconto_pct": desconto_pct,
            "limite_pct": limite_aprovador,
        }), 403

    if not orcamento_repo.autorizar_desconto(orcamento_id, user["id"]):
        return jsonify({"error": "Não foi possível registrar a autorização"}), 500
    _registrar_log_aprovacao(orcamento_id, orc.get("usuario_id"), desconto_pct, user["id"], "aprovado")
    return jsonify({"ok": True, "autorizado_por": user["nome"]})


@api_orcamentos_bp.post("/api/orcamentos/<int:orcamento_id>/rejeitar-desconto")
def rejeitar_desconto(orcamento_id: int):
    """Rejeita o desconto de um orçamento (motivo obrigatório)."""
    data = request.get_json(silent=True) or {}
    motivo = (data.get("motivo") or "").strip()
    if not motivo:
        return jsonify({"error": "Informe o motivo da rejeição"}), 400
    payload = getattr(request, "usuario", None)
    usuario_id = payload.get("sub") if payload else None
    if not usuario_id:
        return jsonify({"error": "Usuário não identificado"}), 401
    orc = orcamento_repo.buscar(orcamento_id)
    if orc is None:
        return jsonify({"error": "Orçamento não encontrado"}), 404
    if not orcamento_repo.rejeitar_desconto(orcamento_id, usuario_id, motivo):
        return jsonify({"error": "Não foi possível registrar a rejeição"}), 500
    _registrar_log_aprovacao(
        orcamento_id, orc.get("usuario_id"),
        float((resumo_desconto(orc) or {}).get("desconto_pct") or 0),
        usuario_id, "rejeitado", motivo,
    )
    return jsonify({"ok": True})


@api_orcamentos_bp.get("/api/orcamentos/pendentes-aprovacao")
def pendentes_aprovacao():
    """Fila do aprovador (MATA094-like): pedidos com desconto pendente que o
    usuário logado pode autorizar (alçada cobre, e não é o vendedor)."""
    payload = getattr(request, "usuario", None)
    usuario_id = payload.get("sub") if payload else None
    if not usuario_id:
        return jsonify({"error": "Usuário não identificado"}), 401
    itens = orcamento_repo.pendentes_aprovacao(usuario_id)
    # Filtra os que a alçada do aprovador realmente cobre (superuser aprova tudo).
    from catalog_server.db import system_conn as _sc_aprov

    with _sc_aprov() as _conn:
        eh_superuser = _conn.execute(
            "SELECT 1 FROM usuario_perfis up JOIN perfis p ON p.id=up.perfil_id"
            " WHERE up.usuario_id=? AND p.nome='Administrador'",
            (usuario_id,),
        ).fetchone() is not None
    user = usuario_repo.get(usuario_id)
    limite_aprovador = float(user.get("desconto_limite_pct") or 0) if user else 0.0
    out = []
    for it in itens:
        orc = orcamento_repo.buscar(it["id"])
        if orc is None:
            continue
        pct = float((resumo_desconto(orc) or {}).get("desconto_pct") or 0)
        if not eh_superuser and pct > limite_aprovador + 1e-6:
            continue
        out.append({**it, "desconto_pct": pct, "limite_aprovador": limite_aprovador})
    return jsonify(out)


def _registrar_log_aprovacao(
    orcamento_id: int, solicitante_id: int | None, desconto_pct: float,
    aprovador_id: int, status: str, motivo: str = "",
) -> None:
    from catalog_server.db import system_conn as _sc

    with _sc() as conn:
        conn.execute(
            "INSERT INTO desconto_aprovacao_log"
            " (orcamento_id, solicitante_id, desconto_pct, aprovador_id, status, motivo)"
            " VALUES (?,?,?,?,?,?)",
            (orcamento_id, solicitante_id, round(float(desconto_pct), 2), aprovador_id, status, motivo),
        )
        conn.commit()


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
