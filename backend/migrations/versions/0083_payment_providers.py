"""Migração 0083 — Integração de pagamentos nas contas a receber (v2.23.0).

Habilita a emissão de boleto e PIX via múltiplos provedores (Asaas, Mercado
Pago na fase 1; EfiPay, Sicoob na fase 2) com troca por prioridade de custo:

- `payment_provider`: catálogo de provedores (asaas/mercadopago/efipay/sicoob).
- `payment_provider_config`: credenciais por provedor + operação (boleto/pix)
  + ambiente (sandbox/producao) + prioridade (custo). A troca de provedor é
  só reordenar a prioridade, sem código.
- `contas_receber`: expandida com provider_id, payment_id, tipo_cobranca,
  status_cobranca, payload_pix, qr_code_base64, txid, webhook_id e
  ultima_consulta_em — para rastrear a cobrança emitida na plataforma e a
  baixa automática via webhook.
- `conta_comprovante`: comprovante anexado na confirmação manual de
  depósito bancário / TED.

Expand-only.
"""
from __future__ import annotations

VERSION = 83
RISCO = "moderada"
NAME = "payment_providers"

MUDANCA = {
    "o_que": [
        "Tabela payment_provider (catálogo: asaas, mercadopago, efipay, sicoob)",
        "Tabela payment_provider_config (credenciais por provedor+operação+ambiente, prioridade de custo)",
        "contas_receber: provider_id, payment_id, tipo_cobranca, status_cobranca, payload_pix, qr_code_base64, txid, webhook_id, ultima_consulta_em",
        "Tabela conta_comprovante (comprovante de depósito/TED na baixa manual)",
        "Seed dos provedores (4) na ativação",
    ],
    "porque": [
        "Financeiro precisa emitir boleto e PIX por conta a receber, com troca de provedor por custo (sandbox primeiro)",
        "Baixa automática via webhook (PIX/boleto) e manual (dinheiro/cheque/depósito/TED com comprovante)",
    ],
}


def guard(conn) -> bool:
    row = conn.execute(
        "SELECT 1 FROM information_schema.tables"
        " WHERE table_schema='public' AND table_name='payment_provider'"
    ).fetchone()
    return row is not None


def forward(conn) -> None:
    ac = conn.autocommit
    conn.autocommit = True
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS payment_provider (
                id         BIGSERIAL PRIMARY KEY,
                codigo     TEXT NOT NULL UNIQUE,
                nome       TEXT NOT NULL,
                ativo      INTEGER NOT NULL DEFAULT 1,
                criado_em  TEXT NOT NULL DEFAULT (to_char(now(),'YYYY-MM-DD HH24:MI:SS'))
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS payment_provider_config (
                id             BIGSERIAL PRIMARY KEY,
                provider_id    BIGINT NOT NULL REFERENCES payment_provider(id) ON DELETE CASCADE,
                operacao       TEXT NOT NULL DEFAULT 'boleto',
                ambiente       TEXT NOT NULL DEFAULT 'sandbox',
                client_id      TEXT DEFAULT '',
                client_secret  TEXT DEFAULT '',
                access_token   TEXT DEFAULT '',
                api_key        TEXT DEFAULT '',
                certificado    TEXT DEFAULT '',
                conta          TEXT DEFAULT '',
                chave_pix      TEXT DEFAULT '',
                prioridade     INTEGER NOT NULL DEFAULT 10,
                ativo          INTEGER NOT NULL DEFAULT 1,
                criado_em      TEXT NOT NULL DEFAULT (to_char(now(),'YYYY-MM-DD HH24:MI:SS')),
                UNIQUE (provider_id, operacao, ambiente)
            )
            """
        )
        conn.execute(
            "ALTER TABLE contas_receber"
            " ADD COLUMN IF NOT EXISTS provider_id BIGINT"
        )
        conn.execute(
            "ALTER TABLE contas_receber"
            " ADD COLUMN IF NOT EXISTS payment_id TEXT DEFAULT ''"
        )
        conn.execute(
            "ALTER TABLE contas_receber"
            " ADD COLUMN IF NOT EXISTS tipo_cobranca TEXT DEFAULT ''"
        )
        conn.execute(
            "ALTER TABLE contas_receber"
            " ADD COLUMN IF NOT EXISTS status_cobranca TEXT DEFAULT 'nao_emitido'"
        )
        conn.execute(
            "ALTER TABLE contas_receber"
            " ADD COLUMN IF NOT EXISTS payload_pix TEXT DEFAULT ''"
        )
        conn.execute(
            "ALTER TABLE contas_receber"
            " ADD COLUMN IF NOT EXISTS qr_code_base64 TEXT DEFAULT ''"
        )
        conn.execute(
            "ALTER TABLE contas_receber"
            " ADD COLUMN IF NOT EXISTS txid TEXT DEFAULT ''"
        )
        conn.execute(
            "ALTER TABLE contas_receber"
            " ADD COLUMN IF NOT EXISTS webhook_id TEXT DEFAULT ''"
        )
        conn.execute(
            "ALTER TABLE contas_receber"
            " ADD COLUMN IF NOT EXISTS ultima_consulta_em TEXT DEFAULT ''"
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS conta_comprovante (
                id          BIGSERIAL PRIMARY KEY,
                conta_id    BIGINT NOT NULL REFERENCES contas_receber(id) ON DELETE CASCADE,
                tipo        TEXT NOT NULL DEFAULT 'deposito',
                filename    TEXT NOT NULL,
                descricao   TEXT NOT NULL DEFAULT '',
                usuario_id  BIGINT REFERENCES usuarios(id),
                criado_em   TEXT NOT NULL DEFAULT (to_char(now(),'YYYY-MM-DD HH24:MI:SS'))
            )
            """
        )
        for codigo, nome in (
            ("asaas", "Asaas"),
            ("mercadopago", "Mercado Pago"),
            ("efipay", "EfiPay"),
            ("sicoob", "Sicoob"),
        ):
            conn.execute(
                "INSERT INTO payment_provider (codigo, nome) VALUES (%s, %s)"
                " ON CONFLICT (codigo) DO NOTHING",
                (codigo, nome),
            )
    finally:
        conn.autocommit = ac


def backward(conn) -> None:
    ac = conn.autocommit
    conn.autocommit = True
    try:
        conn.execute("DROP TABLE IF EXISTS conta_comprovante")
        conn.execute("ALTER TABLE contas_receber DROP COLUMN IF EXISTS ultima_consulta_em")
        conn.execute("ALTER TABLE contas_receber DROP COLUMN IF EXISTS webhook_id")
        conn.execute("ALTER TABLE contas_receber DROP COLUMN IF EXISTS txid")
        conn.execute("ALTER TABLE contas_receber DROP COLUMN IF EXISTS qr_code_base64")
        conn.execute("ALTER TABLE contas_receber DROP COLUMN IF EXISTS payload_pix")
        conn.execute("ALTER TABLE contas_receber DROP COLUMN IF EXISTS status_cobranca")
        conn.execute("ALTER TABLE contas_receber DROP COLUMN IF EXISTS tipo_cobranca")
        conn.execute("ALTER TABLE contas_receber DROP COLUMN IF EXISTS payment_id")
        conn.execute("ALTER TABLE contas_receber DROP COLUMN IF EXISTS provider_id")
        conn.execute("DROP TABLE IF EXISTS payment_provider_config")
        conn.execute("DROP TABLE IF EXISTS payment_provider")
    finally:
        conn.autocommit = ac