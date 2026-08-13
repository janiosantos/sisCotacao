"""0045 - Snapshot fiscal da venda + contexto de destino no orçamento.

`orcamento_itens_fiscal` grava, por item do orçamento, o resultado fiscal usado
na operação (CFOP, CST/CSOSN, ICMS, ST, PIS/COFINS, IBS/CBS, regra/versão). Se a
regra mudar amanhã, a nota emitida ontem reproduz exatamente o cálculo utilizado.

`orcamentos` passa a carregar o contexto do destino (UF, tipo de cliente,
condição de contribuinte, modelo de documento) para montar o contexto fiscal.
"""
from __future__ import annotations

import sqlite3

VERSION = 45
NAME = "Snapshot fiscal da venda e contexto de destino no orçamento"

_COLS_ORCAMENTOS = (
    "uf_destino TEXT",
    "tipo_cliente TEXT",
    "contribuinte TEXT",
    "modelo_documento TEXT",
)

_SQL = """
CREATE TABLE IF NOT EXISTS orcamento_itens_fiscal (
    id                   INTEGER PRIMARY KEY AUTOINCREMENT,
    orcamento_id         INTEGER NOT NULL REFERENCES orcamentos(id) ON DELETE CASCADE,
    item_id              INTEGER NOT NULL REFERENCES orcamento_itens(id) ON DELETE CASCADE,
    variante_id          INTEGER,
    data_operacao        TEXT,
    regime               TEXT,
    ncm                  TEXT,
    cest                 TEXT,
    cfop                 TEXT,
    origem               INTEGER,
    cst_icms             TEXT,
    csosn                TEXT,
    cst_pis              TEXT,
    cst_cofins           TEXT,
    cst_ibs              TEXT,
    cst_cbs              TEXT,
    aliquota_icms        REAL,
    base_icms            REAL,
    valor_icms           REAL,
    modalidade_st        TEXT,
    base_icms_st         REAL,
    aliquota_icms_st     REAL,
    valor_icms_st        REAL,
    aliquota_pis         REAL,
    valor_pis            REAL,
    aliquota_cofins      REAL,
    valor_cofins         REAL,
    aliquota_ibs         REAL,
    valor_ibs            REAL,
    aliquota_cbs         REAL,
    valor_cbs            REAL,
    regra_id             INTEGER,
    regra_nome           TEXT,
    regra_versao         TEXT,
    regra_fonte          TEXT,
    regra_origem         TEXT,
    regra_produto_id     INTEGER,
    regra_produto_nome   TEXT,
    regra_produto_versao TEXT,
    resultado_json       TEXT,
    status_validacao     TEXT,
    criado_em            TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_ofis_orcamento ON orcamento_itens_fiscal(orcamento_id);
CREATE INDEX IF NOT EXISTS idx_ofis_variante ON orcamento_itens_fiscal(variante_id);
"""


def _cols(conn: sqlite3.Connection, table: str) -> set[str]:
    return {r[1] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()}


def guard(conn: sqlite3.Connection) -> bool:
    try:
        return "orcamento_itens_fiscal" in {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
    except sqlite3.OperationalError:
        return False


def forward(conn: sqlite3.Connection) -> None:
    conn.executescript(_SQL)
    for col in _COLS_ORCAMENTOS:
        if col.split()[0] not in _cols(conn, "orcamentos"):
            conn.execute(f"ALTER TABLE orcamentos ADD COLUMN {col}")


def backward(conn: sqlite3.Connection) -> None:
    conn.execute("DROP TABLE IF EXISTS orcamento_itens_fiscal")
    for col in _COLS_ORCAMENTOS:
        name = col.split()[0]
        try:
            conn.execute(f"ALTER TABLE orcamentos DROP COLUMN {name}")
        except sqlite3.OperationalError:
            pass
