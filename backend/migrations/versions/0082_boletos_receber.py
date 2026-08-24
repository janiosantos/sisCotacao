"""Migração 0082 — Boletos de contas a receber (v2.22.0).

Adiciona campos de boleto em `contas_receber` para vendas a prazo:
- `status_boleto`: 'nao_emitido' | 'gerado' | 'impresso' | 'cancelado'
- `linha_digitavel`: linha digitável do boleto (layout 48 dígitos genérico)
- `codigo_barras`: código de barras
- `nosso_numero`: número de controle do boleto
- `url_boleto`: URL pública do boleto (PDF/template) quando aplicável

Sem integração bancária real nesta fase — o boleto é gerado no layout
imprimível (template) e marcado na conta. Expand-only.
"""
from __future__ import annotations

VERSION = 82
RISCO = "moderada"
NAME = "boletos_receber"

MUDANCA = {
    "o_que": [
        "contas_receber: colunas status_boleto, linha_digitavel, codigo_barras, nosso_numero e url_boleto",
        "Backfill: status_boleto='nao_emitido' nas contas existentes",
    ],
    "porque": [
        "Vendas a prazo (cliente identificado + condição ativa) geram parcelas e precisam de boleto imprimível",
        "Pedido finalizado com boleto emitido não pode ser alterado/reaberto",
    ],
}


def guard(conn) -> bool:
    row = conn.execute(
        "SELECT 1 FROM information_schema.columns"
        " WHERE table_name='contas_receber' AND column_name='status_boleto'"
    ).fetchone()
    return row is not None


def forward(conn) -> None:
    ac = conn.autocommit
    conn.autocommit = True
    try:
        conn.execute(
            "ALTER TABLE contas_receber"
            " ADD COLUMN IF NOT EXISTS status_boleto TEXT NOT NULL DEFAULT 'nao_emitido'"
        )
        conn.execute(
            "ALTER TABLE contas_receber"
            " ADD COLUMN IF NOT EXISTS linha_digitavel TEXT DEFAULT ''"
        )
        conn.execute(
            "ALTER TABLE contas_receber"
            " ADD COLUMN IF NOT EXISTS codigo_barras TEXT DEFAULT ''"
        )
        conn.execute(
            "ALTER TABLE contas_receber"
            " ADD COLUMN IF NOT EXISTS nosso_numero TEXT DEFAULT ''"
        )
        conn.execute(
            "ALTER TABLE contas_receber"
            " ADD COLUMN IF NOT EXISTS url_boleto TEXT DEFAULT ''"
        )
        conn.execute(
            "UPDATE contas_receber SET status_boleto='nao_emitido' WHERE status_boleto=''"
        )
    finally:
        conn.autocommit = ac


def backward(conn) -> None:
    ac = conn.autocommit
    conn.autocommit = True
    try:
        conn.execute("ALTER TABLE contas_receber DROP COLUMN IF EXISTS url_boleto")
        conn.execute("ALTER TABLE contas_receber DROP COLUMN IF EXISTS nosso_numero")
        conn.execute("ALTER TABLE contas_receber DROP COLUMN IF EXISTS codigo_barras")
        conn.execute("ALTER TABLE contas_receber DROP COLUMN IF EXISTS linha_digitavel")
        conn.execute("ALTER TABLE contas_receber DROP COLUMN IF EXISTS status_boleto")
    finally:
        conn.autocommit = ac