"""0035 - Condição de pagamento por fornecedor na cotação (compras).

Adiciona as colunas `condicao_pagamento` e `condicao_pagamento_dias` em
`cotacao_fornecedores`: o fornecedor informa a condição de pagamento (texto
livre) e o prazo em dias (quando aplicável) junto com a proposta. A matriz de
comparação passa a exibir a condição por fornecedor e a lógica "Recomendado"
do comprador usa o prazo de pagamento como critério de pontuação.
"""
from __future__ import annotations

import sqlite3

VERSION = 35
NAME = "Condição de pagamento por fornecedor na cotação"

_SQL = """
ALTER TABLE cotacao_fornecedores
    ADD COLUMN condicao_pagamento TEXT;

ALTER TABLE cotacao_fornecedores
    ADD COLUMN condicao_pagamento_dias INTEGER;
"""


def guard(conn: sqlite3.Connection) -> bool:
    try:
        cols = {r[1] for r in conn.execute("PRAGMA table_info(cotacao_fornecedores)").fetchall()}
    except sqlite3.OperationalError:
        return False
    return "condicao_pagamento" in cols


def forward(conn: sqlite3.Connection) -> None:
    conn.executescript(_SQL)


def backward(conn: sqlite3.Connection) -> None:
    for col in ("condicao_pagamento", "condicao_pagamento_dias"):
        try:
            conn.execute(f"ALTER TABLE cotacao_fornecedores DROP COLUMN {col}")
        except sqlite3.OperationalError:
            pass
