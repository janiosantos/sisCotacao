"""Migração 0079 — CRUD de clientes e fornecedores completos (v2.19.0).

Expande o cadastro de clientes e fornecedores inspirado nos sistemas de
referência (TOTVS/MRV):

Clientes:
- `segmento` (profissional/construtora/revenda/varejo/consumidor_final) para
  segmentação e filtros comerciais.
- Apoio fiscal ganha CST-CSOSN, CEST e CFOP separado por operação
  (entrada/saída), alinhado ao motor fiscal.

Fornecedores:
- Colunas de contato (telefone), endereço completo e categoria.
- Condição de pagamento padrão e prazo médio de entrega (dias).
- Avaliação (nota 1..5) e `atualizado_em`.
- Tabela `fornecedor_contatos` (contatos de representantes).

Backfill: valores padrão para os novos campos de clientes/fornecedores
existentes.
"""
from __future__ import annotations

VERSION = 79
RISCO = "moderada"
NAME = "clientes_fornecedores"

MUDANCA = {
    "o_que": [
        "clientes: coluna segmento (profissional/construtora/revenda/varejo/consumidor_final) para segmentação",
        "cliente_apoio_fiscal: colunas cst_csosn, cest, cfop_entrada e cfop_saida (CFOP por operação)",
        "fornecedores: colunas telefone, endereco, numero, bairro, cidade, uf, cep, categoria, condicao_pagamento_id, prazo_entrega_dias, nota, atualizado_em",
        "Nova tabela fornecedor_contatos (contatos de representantes por fornecedor)",
        "Backfill: clientes sem segmento → consumidor_final; fornecedores sem categoria → geral",
    ],
    "porque": [
        "Cadastro de clientes/fornecedores incompleto e pouco funcional frente ao mercado (TOTVS/MRV)",
        "Apoio fiscal do cliente precisa de CSOSN/CEST e CFOP distinto por operação para o motor fiscal",
        "Fornecedor precisa de contatos, endereço, condições comerciais e avaliação para compras e cotações",
    ],
}


def guard(conn) -> bool:
    row = conn.execute(
        "SELECT 1 FROM information_schema.columns"
        " WHERE table_name='clientes' AND column_name='segmento'"
    ).fetchone()
    return row is not None


def forward(conn) -> None:
    ac = conn.autocommit
    conn.autocommit = True
    try:
        # ── Clientes ────────────────────────────────────────────────
        conn.execute(
            "ALTER TABLE clientes"
            " ADD COLUMN IF NOT EXISTS segmento TEXT DEFAULT ''"
        )
        conn.execute(
            "ALTER TABLE clientes"
            " ADD COLUMN IF NOT EXISTS categoria TEXT DEFAULT ''"
        )
        conn.execute(
            "ALTER TABLE cliente_apoio_fiscal"
            " ADD COLUMN IF NOT EXISTS cst_csosn TEXT DEFAULT ''"
        )
        conn.execute(
            "ALTER TABLE cliente_apoio_fiscal"
            " ADD COLUMN IF NOT EXISTS cest TEXT DEFAULT ''"
        )
        conn.execute(
            "ALTER TABLE cliente_apoio_fiscal"
            " ADD COLUMN IF NOT EXISTS cfop_entrada TEXT DEFAULT ''"
        )
        conn.execute(
            "ALTER TABLE cliente_apoio_fiscal"
            " ADD COLUMN IF NOT EXISTS cfop_saida TEXT DEFAULT ''"
        )
        conn.execute(
            "ALTER TABLE cliente_apoio_fiscal"
            " ADD COLUMN IF NOT EXISTS aliquota_icms_st DOUBLE PRECISION NOT NULL DEFAULT 0"
        )

        # ── Fornecedores ────────────────────────────────────────────
        conn.execute(
            "ALTER TABLE fornecedores"
            " ADD COLUMN IF NOT EXISTS telefone TEXT DEFAULT ''"
        )
        conn.execute(
            "ALTER TABLE fornecedores"
            " ADD COLUMN IF NOT EXISTS endereco TEXT DEFAULT ''"
        )
        conn.execute(
            "ALTER TABLE fornecedores"
            " ADD COLUMN IF NOT EXISTS numero TEXT DEFAULT ''"
        )
        conn.execute(
            "ALTER TABLE fornecedores"
            " ADD COLUMN IF NOT EXISTS bairro TEXT DEFAULT ''"
        )
        conn.execute(
            "ALTER TABLE fornecedores"
            " ADD COLUMN IF NOT EXISTS cidade TEXT DEFAULT ''"
        )
        conn.execute(
            "ALTER TABLE fornecedores"
            " ADD COLUMN IF NOT EXISTS uf TEXT DEFAULT ''"
        )
        conn.execute(
            "ALTER TABLE fornecedores"
            " ADD COLUMN IF NOT EXISTS cep TEXT DEFAULT ''"
        )
        conn.execute(
            "ALTER TABLE fornecedores"
            " ADD COLUMN IF NOT EXISTS categoria TEXT DEFAULT ''"
        )
        conn.execute(
            "ALTER TABLE fornecedores"
            " ADD COLUMN IF NOT EXISTS condicao_pagamento_id INTEGER"
        )
        conn.execute(
            "ALTER TABLE fornecedores"
            " ADD COLUMN IF NOT EXISTS prazo_entrega_dias INTEGER NOT NULL DEFAULT 30"
        )
        conn.execute(
            "ALTER TABLE fornecedores"
            " ADD COLUMN IF NOT EXISTS nota NUMERIC(2,1) NOT NULL DEFAULT 5.0"
        )
        conn.execute(
            "ALTER TABLE fornecedores"
            " ADD COLUMN IF NOT EXISTS atualizado_em TEXT DEFAULT ''"
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS fornecedor_contatos (
                id          BIGSERIAL PRIMARY KEY,
                fornecedor_id INTEGER NOT NULL REFERENCES fornecedores(id) ON DELETE CASCADE,
                nome        TEXT NOT NULL,
                cargo       TEXT DEFAULT '',
                telefone    TEXT DEFAULT '',
                email       TEXT DEFAULT '',
                criado_em   TEXT NOT NULL DEFAULT (to_char(now(),'YYYY-MM-DD HH24:MI:SS'))
            )
            """
        )

        # ── Backfill ────────────────────────────────────────────────
        conn.execute(
            "UPDATE clientes SET segmento='consumidor_final'"
            " WHERE segmento IS NULL OR segmento = ''"
        )
        conn.execute(
            "UPDATE fornecedores SET categoria='geral'"
            " WHERE categoria IS NULL OR categoria = ''"
        )
    finally:
        conn.autocommit = ac


def backward(conn) -> None:
    ac = conn.autocommit
    conn.autocommit = True
    try:
        conn.execute("DROP TABLE IF EXISTS fornecedor_contatos")
        conn.execute("ALTER TABLE fornecedores DROP COLUMN IF EXISTS atualizado_em")
        conn.execute("ALTER TABLE fornecedores DROP COLUMN IF EXISTS nota")
        conn.execute("ALTER TABLE fornecedores DROP COLUMN IF EXISTS prazo_entrega_dias")
        conn.execute("ALTER TABLE fornecedores DROP COLUMN IF EXISTS condicao_pagamento_id")
        conn.execute("ALTER TABLE fornecedores DROP COLUMN IF EXISTS categoria")
        conn.execute("ALTER TABLE fornecedores DROP COLUMN IF EXISTS cep")
        conn.execute("ALTER TABLE fornecedores DROP COLUMN IF EXISTS uf")
        conn.execute("ALTER TABLE fornecedores DROP COLUMN IF EXISTS cidade")
        conn.execute("ALTER TABLE fornecedores DROP COLUMN IF EXISTS bairro")
        conn.execute("ALTER TABLE fornecedores DROP COLUMN IF EXISTS numero")
        conn.execute("ALTER TABLE fornecedores DROP COLUMN IF EXISTS endereco")
        conn.execute("ALTER TABLE fornecedores DROP COLUMN IF EXISTS telefone")
        conn.execute("ALTER TABLE cliente_apoio_fiscal DROP COLUMN IF EXISTS aliquota_icms_st")
        conn.execute("ALTER TABLE cliente_apoio_fiscal DROP COLUMN IF EXISTS cfop_saida")
        conn.execute("ALTER TABLE cliente_apoio_fiscal DROP COLUMN IF EXISTS cfop_entrada")
        conn.execute("ALTER TABLE cliente_apoio_fiscal DROP COLUMN IF EXISTS cest")
        conn.execute("ALTER TABLE cliente_apoio_fiscal DROP COLUMN IF EXISTS cst_csosn")
        conn.execute("ALTER TABLE clientes DROP COLUMN IF EXISTS categoria")
        conn.execute("ALTER TABLE clientes DROP COLUMN IF EXISTS segmento")
    finally:
        conn.autocommit = ac