"""
0015 — Caixa e Financeiro (Fase 4).

- `caixa_movimento`   → movimentações do caixa diário (abertura, entrada, saída, sangria, suprimento, fechamento).
- `contas_receber`    → títulos a receber (vendas a prazo, duplicatas).
- `contas_pagar`      → títulos a pagar (compras a prazo, contas diversas).
"""
from __future__ import annotations

import sqlite3

VERSION = 15
NAME = "Caixa e financeiro: caixa_movimento, contas_receber, contas_pagar"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS caixa_movimento (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    tipo              TEXT NOT NULL
                      CHECK(tipo IN ('abertura','entrada','saida','sangria','suprimento','fechamento')),
    descricao         TEXT NOT NULL DEFAULT '',
    valor             REAL NOT NULL,
    saldo_anterior    REAL NOT NULL DEFAULT 0,
    saldo_posterior   REAL NOT NULL DEFAULT 0,
    forma_pagamento   TEXT DEFAULT 'dinheiro',
    plano_conta_id    INTEGER REFERENCES plano_de_contas(id),
    documento         TEXT,
    orcamento_id      INTEGER REFERENCES orcamentos(id),
    usuario_id        INTEGER REFERENCES usuarios(id),
    criado_em         TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS contas_receber (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    cliente           TEXT NOT NULL DEFAULT '',
    cliente_id        INTEGER REFERENCES clientes(id),
    descricao         TEXT NOT NULL DEFAULT '',
    valor             REAL NOT NULL,
    saldo             REAL NOT NULL,
    data_vencimento   TEXT NOT NULL,
    data_emissao      TEXT NOT NULL DEFAULT (date('now')),
    data_recebimento  TEXT,
    plano_conta_id    INTEGER REFERENCES plano_de_contas(id),
    documento         TEXT,
    observacao        TEXT,
    status            TEXT NOT NULL DEFAULT 'aberto'
                      CHECK(status IN ('aberto','parcial','pago','cancelado')),
    criado_em         TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS contas_pagar (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    fornecedor        TEXT NOT NULL DEFAULT '',
    fornecedor_id     INTEGER REFERENCES fornecedores(id),
    descricao         TEXT NOT NULL DEFAULT '',
    valor             REAL NOT NULL,
    saldo             REAL NOT NULL,
    data_vencimento   TEXT NOT NULL,
    data_emissao      TEXT NOT NULL DEFAULT (date('now')),
    data_pagamento    TEXT,
    plano_conta_id    INTEGER REFERENCES plano_de_contas(id),
    documento         TEXT,
    observacao        TEXT,
    status            TEXT NOT NULL DEFAULT 'aberto'
                      CHECK(status IN ('aberto','parcial','pago','cancelado')),
    criado_em         TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_caixa_data ON caixa_movimento(criado_em);
CREATE INDEX IF NOT EXISTS idx_caixa_tipo ON caixa_movimento(tipo);
CREATE INDEX IF NOT EXISTS idx_receber_cliente ON contas_receber(cliente_id);
CREATE INDEX IF NOT EXISTS idx_receber_venc ON contas_receber(data_vencimento);
CREATE INDEX IF NOT EXISTS idx_receber_status ON contas_receber(status);
CREATE INDEX IF NOT EXISTS idx_pagar_fornecedor ON contas_pagar(fornecedor_id);
CREATE INDEX IF NOT EXISTS idx_pagar_venc ON contas_pagar(data_vencimento);
CREATE INDEX IF NOT EXISTS idx_pagar_status ON contas_pagar(status);
"""


def guard(conn: sqlite3.Connection) -> bool:
    try:
        conn.execute("SELECT 1 FROM caixa_movimento LIMIT 1").fetchone()
        conn.execute("SELECT 1 FROM contas_receber LIMIT 1").fetchone()
        conn.execute("SELECT 1 FROM contas_pagar LIMIT 1").fetchone()
    except sqlite3.OperationalError:
        return False
    return True


def forward(conn: sqlite3.Connection) -> None:
    conn.executescript(_SCHEMA)


def backward(conn: sqlite3.Connection) -> None:
    conn.executescript(
        "DROP TABLE IF EXISTS contas_pagar;"
        " DROP TABLE IF EXISTS contas_receber;"
        " DROP TABLE IF EXISTS caixa_movimento;"
    )
