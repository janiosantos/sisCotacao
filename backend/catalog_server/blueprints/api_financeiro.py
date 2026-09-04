from __future__ import annotations

from flask import Blueprint, jsonify, request, send_file

from catalog_server.repositories import adiantamento_repo, caixa_repo, centro_custo_repo, condicao_repo, contas_repo
from catalog_server.services import caixa_sessao, cobranca
from catalog_server.services import classificacao_financeira
from catalog_server.blueprints.api_usuarios import usuario_id_requisicao
from catalog_server import permissao

api_financeiro_bp = Blueprint("api_financeiro", __name__)


def _flag(value, default: bool = False) -> bool:
    if value is None:
        return default
    return value is True or value == 1 or str(value).lower() in {"1", "true", "on", "sim"}


# ─── Sessão de caixa e terminal (VEN-004) ──────────────────


@api_financeiro_bp.post("/api/financeiro/caixa/sessao/abrir")
def abrir_sessao_caixa():
    data = request.get_json(silent=True) or {}
    operador_id = usuario_id_requisicao()
    if not operador_id:
        return jsonify({"error": "operador_id é obrigatório", "code": "operador_obrigatorio"}), 400
    try:
        return jsonify(caixa_sessao.abrir(
            int(operador_id), float(data.get("saldo_inicial") or 0),
            int(data.get("deposito_id") or 1), data.get("terminal"),
        ))
    except ValueError as exc:
        return jsonify({"error": str(exc), "code": "sessao_invalida"}), 400


@api_financeiro_bp.post("/api/financeiro/caixa/sessao/<int:sessao_id>/suprimento")
def suprimento_sessao(sessao_id: int):
    data = request.get_json(silent=True) or {}
    try:
        return jsonify(caixa_sessao.suprimento(sessao_id, float(data.get("valor") or 0), data.get("descricao") or "", usuario_id_requisicao()))
    except LookupError as exc:
        return jsonify({"error": str(exc), "code": "sessao_nao_encontrada"}), 404
    except ValueError as exc:
        return jsonify({"error": str(exc), "code": "sessao_invalida"}), 400


@api_financeiro_bp.post("/api/financeiro/caixa/sessao/<int:sessao_id>/sangria")
def sangria_sessao(sessao_id: int):
    data = request.get_json(silent=True) or {}
    try:
        return jsonify(caixa_sessao.sangria(sessao_id, float(data.get("valor") or 0), data.get("descricao") or "", usuario_id_requisicao()))
    except LookupError as exc:
        return jsonify({"error": str(exc), "code": "sessao_nao_encontrada"}), 404
    except ValueError as exc:
        return jsonify({"error": str(exc), "code": "sessao_invalida"}), 400


@api_financeiro_bp.post("/api/financeiro/caixa/sessao/<int:sessao_id>/fechar")
def fechar_sessao_caixa(sessao_id: int):
    data = request.get_json(silent=True) or {}
    try:
        return jsonify(caixa_sessao.fechar(sessao_id, float(data.get("saldo_contado") or 0), data.get("justificativa")))
    except LookupError as exc:
        return jsonify({"error": str(exc), "code": "sessao_nao_encontrada"}), 404
    except ValueError as exc:
        return jsonify({"error": str(exc), "code": "sessao_invalida"}), 400


@api_financeiro_bp.post("/api/financeiro/caixa/sessao/<int:sessao_id>/aprovar")
def aprovar_sessao_caixa(sessao_id: int):
    data = request.get_json(silent=True) or {}
    aprovador_id = usuario_id_requisicao()
    try:
        return jsonify(caixa_sessao.aprovar(sessao_id, int(aprovador_id)))
    except LookupError as exc:
        return jsonify({"error": str(exc), "code": "sessao_nao_encontrada"}), 404
    except ValueError as exc:
        return jsonify({"error": str(exc), "code": "sessao_invalida"}), 400


@api_financeiro_bp.get("/api/financeiro/caixa/sessao")
def listar_sessoes_caixa():
    return jsonify({"sessoes": caixa_sessao.listar(request.args.get("status"), request.args.get("operador_id", type=int))})


@api_financeiro_bp.get("/api/financeiro/caixa/sessao/<int:sessao_id>")
def detalhe_sessao_caixa(sessao_id: int):
    s = caixa_sessao.detalhe(sessao_id)
    if not s:
        return jsonify({"error": "Sessão não encontrada", "code": "sessao_nao_encontrada"}), 404
    return jsonify(s)


# ─── Cobrança e renegociação (VEN-006) ─────────────────────


@api_financeiro_bp.get("/api/financeiro/cobranca/vencidas")
def listar_vencidas():
    return jsonify({"contas": cobranca.listar_vencidas(request.args.get("cliente_id", type=int))})


@api_financeiro_bp.post("/api/financeiro/cobranca/<int:conta_id>/recalcular")
def recalcular_cobranca(conta_id: int):
    try:
        return jsonify(cobranca.calcular_cobranca(conta_id))
    except LookupError as exc:
        return jsonify({"error": str(exc), "code": "conta_nao_encontrada"}), 404
    except ValueError as exc:
        return jsonify({"error": str(exc), "code": "cobranca_invalida"}), 400


@api_financeiro_bp.post("/api/financeiro/cobranca/<int:conta_id>/renegociar")
def renegociar_conta(conta_id: int):
    data = request.get_json(silent=True) or {}
    try:
        return jsonify(cobranca.renegociar(conta_id, data.get("novas_parcelas") or [], data.get("motivo")))
    except LookupError as exc:
        return jsonify({"error": str(exc), "code": "conta_nao_encontrada"}), 404
    except ValueError as exc:
        return jsonify({"error": str(exc), "code": "renegociacao_invalida"}), 400


@api_financeiro_bp.get("/api/financeiro/cobranca/config")
def obter_cobranca_config():
    return jsonify({"config": cobranca._config()})


@api_financeiro_bp.put("/api/financeiro/cobranca/config")
def atualizar_cobranca_config():
    data = request.get_json(silent=True) or {}
    try:
        return jsonify({"config": cobranca.atualizar_config(float(data["juros_dia_pct"]), float(data["multa_pct"]))})
    except (KeyError, ValueError, TypeError) as exc:
        return jsonify({"error": str(exc), "code": "cobranca_config_invalida"}), 400


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
    formas_validas = {"dinheiro", "pix", "boleto", "cartao_credito", "cartao_debito", "cheque", "ted", "deposito", "outros"}
    forma = (data.get("forma_pagamento") or "dinheiro").strip().lower()
    if forma not in formas_validas:
        return jsonify({"error": "forma_pagamento inválida"}), 400
    payload = getattr(request, "usuario", None) or {}
    result = caixa_repo.movimentar(
        tipo, descricao, valor,
        forma_pagamento=forma,
        plano_conta_id=data.get("plano_conta_id"),
        documento=data.get("documento"),
        orcamento_id=data.get("orcamento_id"),
        usuario_id=payload.get("sub"),
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
    forma = (data.get("forma_pagamento") or "dinheiro").strip().lower()
    if forma not in {"dinheiro", "pix", "boleto", "cartao_credito", "cartao_debito", "cheque", "ted", "deposito", "outros"}:
        return jsonify({"error": "forma_pagamento inválida"}), 400
    try:
        from catalog_server.repositories import caixa_repo

        from catalog_server.db import system_conn

        with system_conn() as conn:
            conta = conn.execute(
                "SELECT * FROM contas_receber WHERE id=? FOR UPDATE", (conta_id,)
            ).fetchone()
            if conta is None:
                return jsonify({"error": "Conta não encontrada"}), 404
            conta = dict(conta)
            result = contas_repo.receber(
                conta_id, valor, data.get("data_recebimento"), _conn=conn
            )
            caixa_repo.movimentar(
                "entrada",
                f"Recebimento {conta['documento'] or ''} — {conta['cliente'] or ''}",
                valor,
                forma_pagamento=forma,
                documento=conta.get("documento") or "",
                usuario_id=(getattr(request, "usuario", None) or {}).get("sub"),
                _conn=conn,
            )
            # baixa automática da cobrança (PIX/boleto) quando paga
            if result.get("status") == "pago":
                conn.execute(
                    "UPDATE contas_receber SET status_cobranca='pago' WHERE id=?",
                    (conta_id,),
                )
        return jsonify({**result, "forma_pagamento": forma})
    except ValueError as e:
        return jsonify({"error": str(e)}), 400


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
    try:
        conta_id = contas_repo.criar_pagar(
            fornecedor, valor, data_vencimento,
            fornecedor_id=data.get("fornecedor_id"),
            descricao=data.get("descricao", ""),
            documento=data.get("documento"),
            plano_conta_id=data.get("plano_conta_id"),
            observacao=data.get("observacao"),
            competencia_value=data.get("competencia") or data.get("data_emissao") or data_vencimento,
            centro_custo_id=data.get("centro_custo_id"),
            exigir_classificacao=_flag(data.get("exigir_classificacao"), True),
        )
    except (ValueError, TypeError) as exc:
        return jsonify({"error": str(exc), "code": "classificacao_invalida"}), 400
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


# ─── Classificação de despesas e competências ──────────────

@api_financeiro_bp.get("/api/financeiro/classificacao/pendencias")
def listar_pendencias_classificacao():
    try:
        return jsonify(classificacao_financeira.listar_pendencias(
            request.args.get("limit", 100, type=int), request.args.get("offset", 0, type=int)
        ))
    except (TypeError, ValueError) as exc:
        return jsonify({"error": str(exc), "code": "paginacao_invalida"}), 400


@api_financeiro_bp.post("/api/financeiro/contas-pagar/<int:conta_id>/classificar")
def classificar_conta_pagar(conta_id: int):
    data = request.get_json(silent=True) or {}
    try:
        if _flag(data.get("aprovar")) and not permissao.tem_permissao(
            usuario_id_requisicao(), "financeiro", "aprovar"
        ):
            return jsonify({"error": "Somente o responsável financeiro pode aprovar a classificação", "code": "permissao_negada"}), 403
        result = classificacao_financeira.classificar_conta(
            conta_id,
            plano_conta_id=int(data["plano_conta_id"]),
            competencia_value=data.get("competencia"),
            centro_custo_id=int(data["centro_custo_id"]) if data.get("centro_custo_id") else None,
            usuario_id=usuario_id_requisicao(),
            observacao=data.get("observacao_classificacao"),
            aprovar=_flag(data.get("aprovar")),
        )
        return jsonify(result)
    except KeyError:
        return jsonify({"error": "plano_conta_id é obrigatório", "code": "classificacao_obrigatoria"}), 400
    except LookupError as exc:
        return jsonify({"error": str(exc), "code": "conta_nao_encontrada"}), 404
    except (ValueError, TypeError) as exc:
        return jsonify({"error": str(exc), "code": "classificacao_invalida"}), 400


@api_financeiro_bp.get("/api/financeiro/contas-pagar/<int:conta_id>/rateio")
def listar_rateio_conta(conta_id: int):
    return jsonify(classificacao_financeira.listar_rateio(conta_id))


@api_financeiro_bp.post("/api/financeiro/contas-pagar/<int:conta_id>/rateio")
def criar_rateio_conta(conta_id: int):
    data = request.get_json(silent=True) or {}
    try:
        return jsonify(classificacao_financeira.criar_rateio(
            conta_id, data.get("items") or [], usuario_id=usuario_id_requisicao()
        ))
    except LookupError as exc:
        return jsonify({"error": str(exc), "code": "conta_nao_encontrada"}), 404
    except (ValueError, TypeError) as exc:
        return jsonify({"error": str(exc), "code": "rateio_invalido"}), 400


@api_financeiro_bp.get("/api/financeiro/competencias")
def listar_competencias():
    return jsonify(classificacao_financeira.listar_competencias())


@api_financeiro_bp.post("/api/financeiro/competencias")
def criar_competencia():
    try:
        return jsonify(classificacao_financeira.criar_competencia(
            request.get_json(silent=True) or {}, usuario_id_requisicao()
        )), 201
    except (ValueError, TypeError) as exc:
        return jsonify({"error": str(exc), "code": "competencia_invalida"}), 400


@api_financeiro_bp.post("/api/financeiro/competencias/<competencia>/status")
def alterar_status_competencia(competencia: str):
    data = request.get_json(silent=True) or {}
    try:
        return jsonify(classificacao_financeira.alterar_status_competencia(
            competencia, data.get("status") or "", usuario_id_requisicao(), data.get("motivo")
        ))
    except LookupError as exc:
        return jsonify({"error": str(exc), "code": "competencia_nao_encontrada"}), 404
    except (ValueError, TypeError) as exc:
        return jsonify({"error": str(exc), "code": "competencia_invalida"}), 400


@api_financeiro_bp.post("/api/financeiro/competencias/<competencia>/fechar")
def fechar_competencia(competencia: str):
    try:
        return jsonify(classificacao_financeira.alterar_status_competencia(
            competencia, "fechada", usuario_id_requisicao(), (request.get_json(silent=True) or {}).get("motivo")
        ))
    except LookupError as exc:
        return jsonify({"error": str(exc), "code": "competencia_nao_encontrada"}), 404
    except ValueError as exc:
        return jsonify({"error": str(exc), "code": "competencia_invalida"}), 400


@api_financeiro_bp.post("/api/financeiro/competencias/<competencia>/reabrir")
def reabrir_competencia(competencia: str):
    try:
        return jsonify(classificacao_financeira.alterar_status_competencia(
            competencia, "reaberta", usuario_id_requisicao(), (request.get_json(silent=True) or {}).get("motivo")
        ))
    except LookupError as exc:
        return jsonify({"error": str(exc), "code": "competencia_nao_encontrada"}), 404
    except ValueError as exc:
        return jsonify({"error": str(exc), "code": "competencia_invalida"}), 400


@api_financeiro_bp.get("/api/financeiro/competencias/<competencia>/apuracao")
def apurar_competencia(competencia: str):
    try:
        return jsonify(classificacao_financeira.apurar_competencia(competencia))
    except LookupError as exc:
        return jsonify({"error": str(exc), "code": "competencia_nao_encontrada"}), 404
    except ValueError as exc:
        return jsonify({"error": str(exc), "code": "competencia_invalida"}), 400


@api_financeiro_bp.get("/api/financeiro/fornecedores/<int:fornecedor_id>/regra-classificacao")
def obter_regra_classificacao_fornecedor(fornecedor_id: int):
    return jsonify(classificacao_financeira.obter_regra_fornecedor(fornecedor_id) or {})


@api_financeiro_bp.put("/api/financeiro/fornecedores/<int:fornecedor_id>/regra-classificacao")
def salvar_regra_classificacao_fornecedor(fornecedor_id: int):
    try:
        return jsonify(classificacao_financeira.salvar_regra_fornecedor(
            fornecedor_id, request.get_json(silent=True) or {}, usuario_id_requisicao()
        ))
    except KeyError:
        return jsonify({"error": "plano_conta_id é obrigatório", "code": "classificacao_obrigatoria"}), 400
    except (ValueError, TypeError) as exc:
        return jsonify({"error": str(exc), "code": "regra_fornecedor_invalida"}), 400


@api_financeiro_bp.get("/api/financeiro/contas-pagar/<int:conta_id>/memoria-classificacao")
def memoria_classificacao_conta(conta_id: int):
    try:
        return jsonify(classificacao_financeira.memoria_classificacao(conta_id))
    except LookupError as exc:
        return jsonify({"error": str(exc), "code": "conta_nao_encontrada"}), 404


# ─── Condições de Pagamento ────────────────────────────────

@api_financeiro_bp.get("/api/condicoes-pagamento")
def listar_condicoes():
    condicoes = condicao_repo.list()
    # O PDV distingue à vista de prazo pelos dados estruturados, nunca pelo
    # texto da condição. O mesmo contrato serve aos demais consumidores.
    for condicao in condicoes:
        condicao["parcelas"] = condicao_repo.list_parcelas(condicao["id"])
    return jsonify(condicoes)


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


# ─── Lançamentos parcelados / recorrentes (v2.25.0) ────────

@api_financeiro_bp.post("/api/financeiro/lote/preview")
def preview_lote():
    """Calcula as parcelas sem gravar (preview no frontend)."""
    from catalog_server.services import lancamentos_lote

    data = request.get_json(silent=True) or {}
    try:
        if data.get("recorrencia"):
            parcelas = lancamentos_lote.calcular_recorrencia(
                data.get("frequencia") or "mensal",
                float(data.get("valor") or 0),
                data.get("primeira") or "",
                int(data.get("n_ocorrencias") or 1),
                dia=data.get("dia"),
            )
        else:
            parcelas = lancamentos_lote.calcular_parcelas(
                data.get("modo") or "manual",
                float(data.get("valor") or 0),
                data.get("data_base") or "",
                condicao_id=data.get("condicao_pagamento_id"),
                n_parcelas=int(data.get("n_parcelas") or 1),
                intervalo_dias=int(data.get("intervalo_dias") or 30),
                datas=data.get("datas"),
            )
        return jsonify({
            "parcelas": parcelas,
            "total": round(sum(float(p["valor"]) for p in parcelas), 2),
            "n": len(parcelas),
        })
    except (ValueError, TypeError) as e:
        return jsonify({"error": str(e)}), 400


def _criar_lote(tabela: str):
    from catalog_server.services import lancamentos_lote

    data = request.get_json(silent=True) or {}
    pessoa = "fornecedor" if tabela == "contas_pagar" else "cliente"
    if not (data.get(pessoa) or "").strip():
        return jsonify({"error": f"informe o {pessoa}"}), 400
    valor = float(data.get("valor") or 0)
    if valor <= 0:
        return jsonify({"error": "valor obrigatório"}), 400
    try:
        if data.get("recorrencia"):
            parcelas = lancamentos_lote.calcular_recorrencia(
                data.get("frequencia") or "mensal",
                valor,
                data.get("primeira") or data.get("data_base") or data.get("data_emissao") or "",
                int(data.get("n_ocorrencias") or 1),
                dia=data.get("dia"),
            )
        else:
            parcelas = lancamentos_lote.calcular_parcelas(
                data.get("modo") or "manual",
                valor,
                data.get("data_base") or data.get("data_emissao") or "",
                condicao_id=data.get("condicao_pagamento_id"),
                n_parcelas=int(data.get("n_parcelas") or 1),
                intervalo_dias=int(data.get("intervalo_dias") or 30),
                datas=data.get("datas"),
            )
    except (ValueError, TypeError) as e:
        return jsonify({"error": str(e)}), 400
    dados_lote = dict(data)
    if data.get("recorrencia"):
        dados_lote["recorrencia"] = data.get("frequencia") or "mensal"
    try:
        ids, grupo = lancamentos_lote.criar_lote(tabela, dados_lote, parcelas)
    except (ValueError, TypeError) as exc:
        return jsonify({"error": str(exc), "code": "classificacao_invalida"}), 400
    return jsonify({"ok": True, "grupo_id": grupo, "ids": ids, "n_parcelas": len(ids)}), 201


@api_financeiro_bp.post("/api/financeiro/pagar/lote")
def pagar_lote():
    return _criar_lote("contas_pagar")


@api_financeiro_bp.post("/api/financeiro/receber/lote")
def receber_lote():
    return _criar_lote("contas_receber")


@api_financeiro_bp.get("/api/financeiro/lote/<tabela>/<grupo_id>")
def ver_lote(tabela: str, grupo_id: str):
    from catalog_server.services import lancamentos_lote

    if tabela not in ("pagar", "receber"):
        return jsonify({"error": "tabela inválida"}), 400
    return jsonify(lancamentos_lote.listar_lote(f"contas_{tabela}", grupo_id))


@api_financeiro_bp.delete("/api/financeiro/lote/<tabela>/<grupo_id>")
def excluir_lote(tabela: str, grupo_id: str):
    from catalog_server.services import lancamentos_lote

    if tabela not in ("pagar", "receber"):
        return jsonify({"error": "tabela inválida"}), 400
    excluidas = lancamentos_lote.excluir_lote(f"contas_{tabela}", grupo_id)
    return jsonify({"ok": True, "excluidas": excluidas})


# ─── Anexo no lançamento (nota/boleto/comprovante) ─────────

@api_financeiro_bp.post("/api/financeiro/anexo/<tabela>/<int:conta_id>")
def anexar_documento(tabela: str, conta_id: int):
    from catalog_server.blueprints.api_usuarios import usuario_id_requisicao

    if tabela not in ("pagar", "receber"):
        return jsonify({"error": "tabela inválida"}), 400
    tipo = (request.form.get("tipo") or "documento").strip()
    descricao = (request.form.get("descricao") or "").strip()
    arquivo = request.files.get("file")
    if not arquivo or not arquivo.filename:
        return jsonify({"error": "Informe o arquivo"}), 400
    import os
    import uuid as _uuid

    ext = os.path.splitext(arquivo.filename)[1].lower() or ".pdf"
    if ext not in {".pdf", ".png", ".jpg", ".jpeg"}:
        return jsonify({"error": "Formato de anexo não permitido (use PDF, PNG ou JPG)"}), 400
    assinatura = arquivo.stream.read(16)
    arquivo.stream.seek(0)
    assinaturas = {
        ".pdf": assinatura.startswith(b"%PDF-"),
        ".png": assinatura.startswith(b"\x89PNG\r\n\x1a\n"),
        ".jpg": assinatura.startswith(b"\xff\xd8\xff"),
        ".jpeg": assinatura.startswith(b"\xff\xd8\xff"),
    }
    if not assinaturas[ext]:
        return jsonify({"error": "O conteúdo não corresponde ao formato informado"}), 400
    filename = f"anexo_{tabela}_{conta_id}_{_uuid.uuid4().hex[:12]}{ext}"
    base = os.environ.get("COMPROVANTES_DIR", "/app/images/comprovantes")
    os.makedirs(base, exist_ok=True)
    arquivo.save(os.path.join(base, filename))
    with system_conn() as conn:
        conn.execute(
            "INSERT INTO conta_anexo (tabela, conta_id, tipo, filename, descricao, usuario_id)"
            " VALUES (?,?,?,?,?,?)",
            (tabela, conta_id, tipo, filename, descricao, usuario_id_requisicao()),
        )
        conn.commit()
    return jsonify({"ok": True, "filename": filename})


@api_financeiro_bp.get("/api/financeiro/anexo/<tabela>/<int:conta_id>")
def listar_anexos(tabela: str, conta_id: int):
    if tabela not in ("pagar", "receber"):
        return jsonify({"error": "tabela inválida"}), 400
    with system_conn() as conn:
        return jsonify([dict(r) for r in conn.execute(
            "SELECT * FROM conta_anexo WHERE tabela=? AND conta_id=? ORDER BY id",
            (tabela, conta_id),
        ).fetchall()])


@api_financeiro_bp.get("/api/financeiro/anexo/<tabela>/<int:conta_id>/download/<path:filename>")
def baixar_anexo(tabela: str, conta_id: int, filename: str):
    """Download autenticado do anexo — valida que o arquivo pertence à conta."""
    import os

    if tabela not in ("pagar", "receber"):
        return jsonify({"error": "tabela inválida"}), 400
    if not filename or "/" in filename or "\\" in filename:
        return jsonify({"error": "arquivo inválido"}), 400
    with system_conn() as conn:
        row = conn.execute(
            "SELECT filename FROM conta_anexo WHERE tabela=? AND conta_id=? AND filename=?",
            (tabela, conta_id, filename),
        ).fetchone()
    if not row:
        return jsonify({"error": "anexo não encontrado"}), 404
    base = os.environ.get("COMPROVANTES_DIR", "/app/images/comprovantes")
    caminho = os.path.join(base, filename)
    if not os.path.isfile(caminho):
        return jsonify({"error": "arquivo não encontrado"}), 404
    return send_file(caminho, as_attachment=True, download_name=filename)
