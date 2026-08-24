"""Migração 0074 — gatilhos contábeis configuráveis por evento (v2.15.0).

Regras configuráveis que conectam eventos de negócio (venda autorizada, compra,
ajuste de estoque) ao `contabil.lancar()` — a função já existia, faltava a
configuração de quais contas de débito/crédito usar por evento.

Expand (etapa A): nada é removido; `lancamento_contabil` continua o destino.
"""
from __future__ import annotations

VERSION = 74
RISCO = "melhoria"
NAME = "contabil_gatilhos"

MUDANCA = {
    "o_que": [
        "Cria contabil_gatilho (evento_tipo PK, ativo, debito_conta_id, credito_conta_id, descricao)",
        "Semeia os 3 gatilhos padrão (venda_autorizada, compra, ajuste) INATIVOS — só passam a lançar após configurados",
    ],
    "porque": [
        "Conectar eventos de negócio ao contabil.lancar() com contas configuráveis (v2.15.0)",
        "Default inativo preserva comportamento atual até o usuário configurar (expand, sem surpresa)",
    ],
}


def guard(conn) -> bool:
    return conn.execute(
        "SELECT 1 FROM information_schema.tables WHERE table_name='contabil_gatilho'"
    ).fetchone() is not None


def forward(conn) -> None:
    ac = conn.autocommit
    conn.autocommit = True
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS contabil_gatilho (
                evento_tipo TEXT PRIMARY KEY,
                ativo INTEGER NOT NULL DEFAULT 0,
                debito_conta_id BIGINT REFERENCES plano_de_contas(id),
                credito_conta_id BIGINT REFERENCES plano_de_contas(id),
                descricao TEXT NOT NULL DEFAULT '',
                atualizado_em TIMESTAMP NOT NULL DEFAULT now()
            )
            """
        )
        conn.execute(
            """
            INSERT INTO contabil_gatilho (evento_tipo, ativo, descricao) VALUES
            ('venda_autorizada', 0, 'Venda autorizada/faturada — receita'),
            ('compra', 0, 'Compra/pedido de compra — custo da mercadoria'),
            ('ajuste', 0, 'Ajuste de estoque — divergência/regularização')
            ON CONFLICT (evento_tipo) DO NOTHING
            """
        )
    finally:
        conn.autocommit = ac


def backward(conn) -> None:
    ac = conn.autocommit
    conn.autocommit = True
    try:
        conn.execute("DROP TABLE IF EXISTS contabil_gatilho")
    finally:
        conn.autocommit = ac