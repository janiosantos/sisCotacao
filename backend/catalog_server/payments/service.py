"""Orquestração de pagamentos nas contas a receber.

- `emitir`: escolhe o provedor por prioridade de custo, emite boleto/PIX e
  grava os dados na conta a receber.
- `processar_webhook`: valida evento, localiza a conta por payment_id e faz a
  baixa automática (idempotente por webhook_id).
"""
from __future__ import annotations

from catalog_server.db import system_conn
from catalog_server.payments import registry
from catalog_server.repositories import contas_repo


def _emitente() -> dict | None:
    from catalog_server.repositories.fiscal_avancado import emitente_repo

    return emitente_repo.get()


def _salvar_cobranca(
    conta_id: int,
    dados: dict,
    operacao: str,
    ambiente: str,
    provider_id: int,
    _conn=None,
) -> None:
    if _conn is None:
        with system_conn() as conn:
            _salvar_cobranca(
                conta_id, dados, operacao, ambiente, provider_id, _conn=conn
            )
        return
    _conn.execute(
        """UPDATE contas_receber SET
             provider_id=?, payment_id=?, tipo_cobranca=?, status_cobranca=?,
             ambiente_cobranca=?,
             payload_pix=?, qr_code_base64=?, txid=?,
             url_boleto=?, nosso_numero=?, linha_digitavel=?, codigo_barras=?,
             webhook_id=COALESCE(webhook_id, '')
           WHERE id=?""",
        (
            provider_id,
            dados.get("payment_id") or "",
            operacao,
            dados.get("status_cobranca") or "pendente",
            ambiente,
            dados.get("payload_pix") or "",
            dados.get("qr_code_base64") or "",
            dados.get("txid") or "",
            dados.get("url_boleto") or "",
            dados.get("nosso_numero") or "",
            dados.get("linha_digitavel") or "",
            dados.get("codigo_barras") or "",
            conta_id,
        ),
    )


def emitir(conta_id: int, operacao: str, ambiente: str = "sandbox") -> dict:
    """Emite boleto ou PIX para a conta e grava os dados na conta a receber."""
    with system_conn() as conn:
        row = conn.execute(
            """SELECT cr.*, c.doc AS cliente_doc, c.email AS cliente_email, c.tipo_pessoa
               FROM contas_receber cr
               LEFT JOIN clientes c ON c.id=cr.cliente_id
               WHERE cr.id=? FOR UPDATE OF cr""",
            (conta_id,),
        ).fetchone()
        conta = dict(row) if row else None
        if conta is None:
            raise ValueError("Conta não encontrada")
        if conta["status"] == "pago":
            raise ValueError("Conta já paga")
        if conta.get("payment_id"):
            if conta.get("tipo_cobranca") == operacao:
                return {
                    "payment_id": conta["payment_id"],
                    "status_cobranca": conta.get("status_cobranca") or "pendente",
                    "operacao": operacao,
                    "provider": conta.get("provider_id"),
                    "duplicado": True,
                }
            raise ValueError("Conta já possui cobrança em outra operação")

        provider = registry.escolher(operacao, ambiente)
        # O lock da conta permanece até persistir o resultado. Assim, duas
        # requisições simultâneas não emitem duas cobranças externas.
        provider.cfg["payment_id"] = f"siscom-conta-{conta_id}-{operacao}"
        emitente = _emitente()
        if operacao == "pix":
            dados = provider.emitir_pix(conta)
        else:
            dados = provider.emitir_boleto(conta, emitente or {})
        _salvar_cobranca(
            conta_id,
            dados,
            operacao,
            ambiente,
            int(provider.cfg["provider_id"]),
            _conn=conn,
        )
        conn.commit()
        return {**dados, "operacao": operacao, "provider": provider.codigo}


def consultar(conta_id: int) -> dict:
    """Consulta o status da cobrança na plataforma e atualiza a conta."""
    conta = contas_repo.get_receber(conta_id)
    if conta is None:
        raise ValueError("Conta não encontrada")
    payment_id = conta.get("payment_id")
    if not payment_id or not conta.get("provider_id"):
        return {"status_cobranca": "nao_emitido"}
    provider = registry.instanciar_por_conta(conta)
    st = provider.consultar(payment_id)
    if st.get("status_cobranca") == "pago" and conta["status"] != "pago":
        from catalog_server.repositories import caixa_repo

        with system_conn() as conn:
            atual = conn.execute(
                "SELECT * FROM contas_receber WHERE id=? FOR UPDATE", (conta_id,)
            ).fetchone()
            if atual is not None and atual["status"] != "pago":
                atual = dict(atual)
                valor = float(atual["saldo"] or 0)
                contas_repo.receber(conta_id, valor, _conn=conn)
                caixa_repo.movimentar(
                    "entrada",
                    f"Consulta de recebimento {atual['documento'] or ''} — {atual['cliente'] or ''}",
                    valor,
                    forma_pagamento=(
                        "pix" if (atual.get("tipo_cobranca") or "pix") == "pix" else "boleto"
                    ),
                    documento=atual.get("documento") or "",
                    _conn=conn,
                )
                conn.execute(
                    "UPDATE contas_receber SET status_cobranca='pago', ultima_consulta_em=now() WHERE id=?",
                    (conta_id,),
                )
    else:
        with system_conn() as conn:
            conn.execute(
                "UPDATE contas_receber SET status_cobranca=?, ultima_consulta_em=now() WHERE id=?",
                (st.get("status_cobranca") or "pendente", conta_id),
            )
            conn.commit()
    return st


def processar_webhook(
    provider_codigo: str,
    payload: dict,
    headers: dict,
    query: dict | None = None,
) -> dict:
    """Processa o webhook e baixa conta e caixa em uma única transação."""
    # Pré-localiza a conta pelo payment_id para saber operação e ambiente.
    pre_payment_id = None
    try:
        evento_tmp = registry.instanciar(
            provider_codigo, "pix", "sandbox"
        ).webhook(payload, headers)
        if evento_tmp:
            pre_payment_id = evento_tmp.get("payment_id")
    except Exception:
        evento_tmp = None

    with system_conn() as conn:
        row = conn.execute(
            "SELECT * FROM contas_receber WHERE payment_id=? LIMIT 1",
            (pre_payment_id or "",),
        ).fetchone()
        conta = dict(row) if row else None

    operacao = (conta["tipo_cobranca"] or "pix") if conta else "pix"
    ambiente = (conta.get("ambiente_cobranca") if conta else None) or "sandbox"
    provider = registry.instanciar(provider_codigo, operacao, ambiente)

    # Validação de autenticidade antes de qualquer processamento.
    provider.validar_assinatura(payload, headers, query)

    evento = provider.webhook(payload, headers)
    if not evento:
        return {"ok": True, "ignorado": True}

    payment_id = evento.get("payment_id")
    webhook_id = evento.get("webhook_id") or payment_id
    if not payment_id:
        return {"ok": True, "ignorado": True}

    from catalog_server.repositories import caixa_repo

    with system_conn() as conn:
        row = conn.execute(
            "SELECT * FROM contas_receber WHERE payment_id=? FOR UPDATE",
            (payment_id,),
        ).fetchone()
        if row is None:
            return {"ok": True, "ignorado": True}
        conta = dict(row)  # PgRow não tem .get — normaliza antes de usar.
        if conta["webhook_id"] == webhook_id:
            return {"ok": True, "duplicado": True}
        if conta["status"] == "pago":
            return {"ok": True, "ignorado": True}
        if evento.get("status_cobranca") != "pago":
            return {"ok": True, "ignorado": True}

        valor = float(conta["saldo"] or 0)
        conn.execute(
            "UPDATE contas_receber SET status='pago', saldo=0, status_cobranca='pago',"
            " data_recebimento=now(), webhook_id=? WHERE id=?",
            (webhook_id, conta["id"]),
        )
        caixa_repo.movimentar(
            "entrada",
            f"Recebimento {conta['documento'] or ''} — {conta['cliente'] or ''} (webhook {provider_codigo})",
            valor,
            forma_pagamento="pix" if operacao == "pix" else "boleto",
            documento=conta.get("documento") or "",
            _conn=conn,
        )
        conn.commit()
        return {"ok": True, "conta_id": int(conta["id"]), "valor": valor}
