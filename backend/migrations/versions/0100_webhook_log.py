"""Migração 0100 — log de webhooks de pagamento + rechecagem.

Cria a tabela `webhook_log` para registrar toda notificação recebida dos
provedores (Asaas, Mercado Pago, EfiPay, Sicoob, TecnoSpeed): evento,
payment_id, resultado (processado/duplicado/ignorado/erro/nao_autorizado/
payload_invalido), HTTP retornado, validade da assinatura, IP e resumo do
payload — para acompanhamento e auditoria.
"""
from __future__ import annotations

VERSION = 100
RISCO = "moderada"
NAME = "webhook_log"

MUDANCA = {
    "o_que": ["Cria tabela webhook_log para auditoria das notificações de pagamento"],
    "porque": [
        "Permite acompanhar as notificações recebidas, o resultado de cada uma e fazer rechecagem em lotes",
        "Sem log, falhas de entrega/baixa não são visíveis para o operador",
    ],
}


def guard(conn) -> bool:
    row = conn.execute(
        "SELECT 1 FROM information_schema.tables "
        "WHERE table_schema='public' AND table_name='webhook_log'"
    ).fetchone()
    return bool(row)


def forward(conn) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS webhook_log (
            id BIGSERIAL PRIMARY KEY,
            provider TEXT NOT NULL,
            evento TEXT,
            payment_id TEXT,
            status TEXT NOT NULL,
            http_status INTEGER,
            assinatura_ok BOOLEAN,
            ip TEXT,
            payload TEXT,
            erro TEXT,
            criado_em TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_webhook_log_provider_criado "
        "ON webhook_log (provider, criado_em DESC)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_webhook_log_payment "
        "ON webhook_log (payment_id)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_webhook_log_status_criado "
        "ON webhook_log (status, criado_em DESC)"
    )
    conn.commit()


def backward(conn) -> None:
    conn.execute("DROP TABLE IF EXISTS webhook_log")