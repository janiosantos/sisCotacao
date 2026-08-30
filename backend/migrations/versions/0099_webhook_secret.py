"""Migração 0099 — segredo do webhook por provedor de pagamento.

Expand-only: adiciona `webhook_secret` à config do provedor de pagamento,
permitindo validar a assinatura/token nativo de cada plataforma (Asaas,
Mercado Pago, EfiPay, Sicoob, TecnoSpeed) sem usar a mesma credencial da
API de emissão. A validação é feita por provedor em `catalog_server/payments/`.
"""
from __future__ import annotations

VERSION = 99
RISCO = "moderada"
NAME = "webhook_secret"

MUDANCA = {
    "o_que": ["payment_provider_config: coluna webhook_secret"],
    "porque": [
        "Validação de assinatura/token nativo do webhook por provedor",
        "Separa o segredo do webhook das credenciais de emissão (Asaas recomenda não usar a API Key)",
    ],
}


def guard(conn) -> bool:
    row = conn.execute(
        "SELECT 1 FROM information_schema.columns "
        "WHERE table_schema='public' AND table_name='payment_provider_config' "
        "AND column_name='webhook_secret'"
    ).fetchone()
    return row is not None


def forward(conn) -> None:
    conn.execute(
        "ALTER TABLE payment_provider_config "
        "ADD COLUMN IF NOT EXISTS webhook_secret TEXT NOT NULL DEFAULT ''"
    )


def backward(conn) -> None:
    conn.execute(
        "ALTER TABLE payment_provider_config DROP COLUMN IF EXISTS webhook_secret"
    )