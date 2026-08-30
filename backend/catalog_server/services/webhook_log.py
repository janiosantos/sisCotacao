"""Log de webhooks de pagamento + rechecagem em lotes.

- `registrar`: grava cada notificação recebida (resultado, HTTP, assinatura, IP,
  resumo do payload) para auditoria.
- `listar`/`detalhe`: consulta dos logs (filtros por provedor/status/data).
- `rechecagem`: para contas a receber com cobrança emitida e ainda não pagas,
  consulta o provedor (payment_id) e baixa automaticamente as que aparecerem
  como pagas — cobre webhooks perdidos/falhos.
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta

from catalog_server.db import system_conn
from catalog_server.payments import registry

_PAYLOAD_MAX = 1000  # caracteres do payload gravado no log


def registrar(
    provider: str,
    status: str,
    http_status: int | None = None,
    assinatura_ok: bool | None = None,
    ip: str | None = None,
    payload: dict | None = None,
    erro: str | None = None,
    evento: str | None = None,
    payment_id: str | None = None,
) -> int:
    """Grava um log de webhook. Nunca lança exceção (não derruba o webhook)."""
    try:
        if payload is not None:
            try:
                texto = json.dumps(payload, ensure_ascii=False, default=str)
            except Exception:
                texto = str(payload)[:_PAYLOAD_MAX]
            if len(texto) > _PAYLOAD_MAX:
                texto = texto[:_PAYLOAD_MAX] + "…"
        else:
            texto = None
        with system_conn() as conn:
            cur = conn.execute(
                "INSERT INTO webhook_log (provider, evento, payment_id, status,"
                " http_status, assinatura_ok, ip, payload, erro)"
                " VALUES (?,?,?,?,?,?,?,?,?) RETURNING id",
                (provider, evento, payment_id, status, http_status,
                 assinatura_ok, ip, texto, (erro or "")[:500]),
            )
            row = cur.fetchone()
            conn.commit()
            return int(row[0])
    except Exception:
        return 0


def listar(provider: str = "", status: str = "", desde: str = "", limite: int = 50, offset: int = 0) -> tuple[list[dict], int]:
    with system_conn() as conn:
        where = ["1=1"]
        params: list = []
        if provider:
            where.append("provider=?")
            params.append(provider)
        if status:
            where.append("status=?")
            params.append(status)
        if desde:
            where.append("criado_em >= ?")
            params.append(desde)
        where_sql = " AND ".join(where)
        total = conn.execute(
            f"SELECT COUNT(*) AS n FROM webhook_log WHERE {where_sql}", params
        ).fetchone()["n"]
        rows = conn.execute(
            f"""SELECT id, provider, evento, payment_id, status, http_status,
                       assinatura_ok, ip, criado_em
                FROM webhook_log WHERE {where_sql}
                ORDER BY criado_em DESC LIMIT ? OFFSET ?""",
            params + [limite, offset],
        ).fetchall()
    return [dict(r) for r in rows], int(total)


def detalhe(log_id: int) -> dict | None:
    with system_conn() as conn:
        row = conn.execute(
            "SELECT * FROM webhook_log WHERE id=?", (log_id,)
        ).fetchone()
    return dict(row) if row else None


def _baixar(conn, conta: dict, payment_id: str, valor: float) -> None:
    """Marca a conta como paga (rechecagem) — idempotente por payment_id."""
    conn.execute(
        "UPDATE contas_receber SET status='pago', saldo=0, status_cobranca='pago',"
        " data_recebimento=now(), webhook_id=COALESCE(webhook_id, 'recheck:'||?)"
        " WHERE id=? AND status<>'pago'",
        (payment_id, conta["id"]),
    )


def rechecagem(provider: str = "", limite: int = 50, payment_id: str = "") -> dict:
    """Consulta o provedor das cobranças pendentes e baixa as pagas.

    Filtros opcionais: `provider` (asaas/mercadopago/...), `limite` e
    `payment_id` (rechecagem de uma conta específica).
    Retorna {verificadas, pagas, ja_pagas, erros, detalhes}.
    """
    from catalog_server.repositories import caixa_repo

    with system_conn() as conn:
        where = ["payment_id IS NOT NULL", "payment_id<>''", "status<>'pago'"]
        params: list = []
        if provider:
            where.append("provider_id IN (SELECT id FROM payment_provider WHERE codigo=?)")
            params.append(provider)
        if payment_id:
            where.append("c.payment_id=?")
            params.append(payment_id)
        where_sql = " AND ".join(where)
        contas = [
            dict(r) for r in conn.execute(
                f"""SELECT c.*, p.codigo AS provider_codigo
                    FROM contas_receber c
                    LEFT JOIN payment_provider p ON p.id=c.provider_id
                    WHERE {where_sql} ORDER BY c.id LIMIT ?""",
                params + [int(limite)],
            ).fetchall()
        ]

    verificadas = pagas = ja_pagas = 0
    erros: list[str] = []
    detalhes: list[dict] = []
    for conta in contas:
        pid = conta.get("payment_id") or ""
        codigo = conta.get("provider_codigo") or provider
        operacao = (conta.get("tipo_cobranca") or "pix")
        ambiente = (conta.get("ambiente_cobranca") or "sandbox")
        try:
            prov = registry.instanciar(codigo, operacao, ambiente)
            st = prov.consultar(pid)
        except Exception as exc:
            erros.append(f"conta {conta.get('id')} ({pid}): {exc}")
            registrar(codigo, "erro", evento="rechecagem", payment_id=pid,
                      erro=f"rechecagem: {exc}")
            continue
        verificadas += 1
        if st.get("status_cobranca") != "pago":
            continue
        with system_conn() as conn:
            atual = conn.execute(
                "SELECT * FROM contas_receber WHERE id=? FOR UPDATE",
                (conta["id"],),
            ).fetchone()
            if atual is None or atual["status"] == "pago":
                ja_pagas += 1
                continue
            valor = float(atual["saldo"] or 0)
            _baixar(conn, dict(atual), pid, valor)
            conn.commit()
        # lança no caixa (entrada)
        try:
            caixa_repo.movimentar(
                "entrada",
                f"Rechecagem {atual['documento'] or ''} — {atual['cliente'] or ''} ({codigo})",
                valor,
                forma_pagamento="pix" if operacao == "pix" else "boleto",
                documento=atual.get("documento") or "",
            )
        except Exception as exc:
            erros.append(f"caixa conta {conta.get('id')}: {exc}")
        pagas += 1
        detalhes.append({"conta_id": conta["id"], "payment_id": pid, "valor": valor})
        registrar(codigo, "processado", evento="rechecagem", payment_id=pid,
                  erro="rechecagem baixou conta", http_status=200)

    return {
        "verificadas": verificadas,
        "pagas": pagas,
        "ja_pagas": ja_pagas,
        "erros": erros,
        "detalhes": detalhes,
        "tempo": datetime.now().isoformat(),
    }