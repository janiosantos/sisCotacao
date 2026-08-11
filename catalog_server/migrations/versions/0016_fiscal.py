"""
0016 — Tabelas Fiscais (Fase 6).

CFOP, CST e configuração fiscal por produto:

- `cfop`             → tabela de CFOP (entrada/saída, mesma UF/outra UF).
- `cst_icms`         → CST ICMS.
- `cst_pis`          → CST PIS.
- `cst_cofins`       → CST COFINS.
- `fiscal_config`    → configuração fiscal por variante (NCM, CFOP, CST, alíquotas).
"""
from __future__ import annotations

import sqlite3

VERSION = 16
NAME = "Tabelas fiscais: CFOP, CST e configuração por produto"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS cfop (
    codigo    TEXT PRIMARY KEY,
    descricao TEXT NOT NULL,
    tipo      TEXT NOT NULL DEFAULT 'saida'
              CHECK(tipo IN ('entrada','saida','mesma_uf','outra_uf'))
);

CREATE TABLE IF NOT EXISTS cst_icms (
    codigo    TEXT PRIMARY KEY,
    descricao TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS cst_pis (
    codigo    TEXT PRIMARY KEY,
    descricao TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS cst_cofins (
    codigo    TEXT PRIMARY KEY,
    descricao TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS fiscal_config (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    variante_id     INTEGER NOT NULL REFERENCES variantes(id) ON DELETE CASCADE,
    ncm             TEXT DEFAULT '',
    cfop            TEXT,
    cst_icms        TEXT,
    cst_pis         TEXT,
    cst_cofins      TEXT,
    aliquota_icms   REAL DEFAULT 0,
    aliquota_pis    REAL DEFAULT 0,
    aliquota_cofins REAL DEFAULT 0,
    aliquota_ipi    REAL DEFAULT 0,
    UNIQUE(variante_id)
);

CREATE INDEX IF NOT EXISTS idx_fiscal_var ON fiscal_config(variante_id);
"""

SEED_CFOP = [
    ("1.102", "Compra para industrialização", "entrada"),
    ("1.111", "Compra para revenda", "entrada"),
    ("1.204", "Compra para revenda (outra UF)", "outra_uf"),
    ("5.102", "Venda de mercadoria adquirida", "saida"),
    ("5.109", "Venda de mercadoria adquirida (NF-e)", "saida"),
    ("6.102", "Venda de mercadoria adquirida (outra UF)", "outra_uf"),
    ("5.405", "Venda de mercadoria (consumidor final)", "saida"),
    ("6.405", "Venda de mercadoria (consumidor final, outra UF)", "outra_uf"),
    ("5.101", "Venda de produção do estabelecimento", "saida"),
    ("2.102", "Devolução de compra para revenda", "entrada"),
    ("2.202", "Devolução de compra para industrialização", "entrada"),
    ("5.201", "Devolução de venda", "saida"),
    ("1.949", "Outra entrada de mercadoria", "entrada"),
    ("5.949", "Outra saída de mercadoria", "saida"),
]

SEED_CST_ICMS = [
    ("00", "Tributada integralmente"),
    ("10", "Tributada com cobrança de ICMS por ST"),
    ("20", "Base de cálculo reduzida"),
    ("30", "Isenta ou não tributada (ST anula ICMS)"),
    ("40", "Isenta"),
    ("41", "Não tributada"),
    ("50", "Suspensão"),
    ("51", "Diferimento"),
    ("60", "ICMS cobrado anteriormente por ST"),
    ("70", "Redução de base + ST"),
    ("90", "Outras"),
]

SEED_CST_PIS = [
    ("01", "Operação Tributável - Alíquota Básica"),
    ("02", "Operação Tributável - Alíquota Diferenciada"),
    ("03", "Operação Tributável - Alíquota por Unidade"),
    ("04", "Operação Tributável - Alíquota Zero"),
    ("05", "Operação Tributável - ST (Substituição Tributária)"),
    ("06", "Operação Tributável - Alíquuta Zero (ST)"),
    ("07", "Operação Isenta da Contribuição"),
    ("08", "Operação sem Incidência da Contribuição"),
    ("09", "Operação com Suspensão da Contribuição"),
    ("49", "Outras Operações de Saída"),
    ("50", "Operação com Direito a Crédito"),
    ("51", "Operação sem Direito a Crédito"),
    ("52", "Operação com Crédito Presumido"),
    ("53", "Operação com Alíquota por Unidade"),
    ("54", "Operação com Alíquota por Unidade (Direito a Crédito)"),
    ("55", "Operação com Alíquota por Unidade (sem Direito a Crédito)"),
    ("98", "Outras"),
    ("99", "Outras Operações"),
]

SEED_CST_COFINS = SEED_CST_PIS  # mesmos códigos


def guard(conn: sqlite3.Connection) -> bool:
    try:
        conn.execute("SELECT 1 FROM cfop LIMIT 1").fetchone()
        conn.execute("SELECT 1 FROM cst_icms LIMIT 1").fetchone()
        conn.execute("SELECT 1 FROM fiscal_config LIMIT 1").fetchone()
    except sqlite3.OperationalError:
        return False
    return True


def forward(conn: sqlite3.Connection) -> None:
    conn.executescript(_SCHEMA)
    # Seed CFOP
    if not conn.execute("SELECT 1 FROM cfop LIMIT 1").fetchone():
        conn.executemany("INSERT OR IGNORE INTO cfop (codigo, descricao, tipo) VALUES (?,?,?)", SEED_CFOP)
    # Seed CST ICMS
    if not conn.execute("SELECT 1 FROM cst_icms LIMIT 1").fetchone():
        conn.executemany("INSERT OR IGNORE INTO cst_icms (codigo, descricao) VALUES (?,?)", SEED_CST_ICMS)
    # Seed CST PIS
    if not conn.execute("SELECT 1 FROM cst_pis LIMIT 1").fetchone():
        conn.executemany("INSERT OR IGNORE INTO cst_pis (codigo, descricao) VALUES (?,?)", SEED_CST_PIS)
    # Seed CST COFINS
    if not conn.execute("SELECT 1 FROM cst_cofins LIMIT 1").fetchone():
        conn.executemany("INSERT OR IGNORE INTO cst_cofins (codigo, descricao) VALUES (?,?)", SEED_CST_COFINS)
    # Copia NCM de variantes para fiscal_config se ainda não existir
    if not conn.execute("SELECT 1 FROM fiscal_config LIMIT 1").fetchone():
        vars_ncm = conn.execute("SELECT id, ncm FROM variantes WHERE ncm IS NOT NULL AND ncm != ''").fetchall()
        if vars_ncm:
            conn.executemany(
                "INSERT OR IGNORE INTO fiscal_config (variante_id, ncm) VALUES (?,?)",
                [(v["id"], v["ncm"]) for v in vars_ncm],
            )


def backward(conn: sqlite3.Connection) -> None:
    conn.executescript(
        "DROP TABLE IF EXISTS fiscal_config;"
        " DROP TABLE IF EXISTS cfop;"
        " DROP TABLE IF EXISTS cst_icms;"
        " DROP TABLE IF EXISTS cst_pis;"
        " DROP TABLE IF EXISTS cst_cofins;"
    )
