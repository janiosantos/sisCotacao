"""0037 - Modelo fiscal avançado: CEST, CSOSN, benefícios, ICMS-ST/DIFAL.

Complementa o modelo fiscal existente (cfop, cst_*, fiscal_config, ibpt,
emitente) sem duplicar nada:

- `cest`               → Código Especificador da Substituição Tributária por NCM.
- `csosn`              → Código do Simples Nacional (CRT 1/2/3).
- `beneficios_fiscais` → benefícios (isenção, redução de base, crédito presumido,
                         diferimento, suspensão) com vigência.
- `fiscal_config`      → novas colunas por variante: origem da mercadoria, CEST,
                         CSOSN, ICMS-ST (alíquota, MVA, redução de base), DIFAL
                         (interestadual, FECP), crédito de ICMS, benefício e
                         vigência da configuração.

O cálculo em si (carga tributária / crédito) será o Motor Fiscal (etapa 2).
"""
from __future__ import annotations

import sqlite3

VERSION = 37
NAME = "Modelo fiscal avançado: CEST, CSOSN, benefícios e ICMS-ST/DIFAL"

_COLS_FISCAL_CONFIG = (
    "origem INTEGER DEFAULT 0",
    "cest TEXT DEFAULT ''",
    "csosn TEXT DEFAULT ''",
    "aliquota_icms_st REAL DEFAULT 0",
    "mva REAL DEFAULT 0",
    "base_reducao REAL DEFAULT 0",
    "aliquota_interestadual REAL DEFAULT 0",
    "aliquota_fecp REAL DEFAULT 0",
    "credito_icms REAL DEFAULT 0",
    "beneficio_id INTEGER REFERENCES beneficios_fiscais(id)",
    "vigencia_inicio TEXT",
    "vigencia_fim TEXT",
)

_SCHEMA = """
CREATE TABLE IF NOT EXISTS cest (
    codigo          TEXT PRIMARY KEY,
    ncm_prefix      TEXT DEFAULT '',
    descricao       TEXT DEFAULT '',
    vigencia_inicio TEXT,
    vigencia_fim    TEXT,
    ativo           INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS csosn (
    codigo    TEXT PRIMARY KEY,
    descricao TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS beneficios_fiscais (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    codigo          TEXT NOT NULL UNIQUE,
    descricao       TEXT DEFAULT '',
    tipo            TEXT NOT NULL DEFAULT 'reducao_base'
                    CHECK(tipo IN ('isencao','reducao_base','credito_presumido','diferimento','suspensao')),
    valor_default   REAL DEFAULT 0,
    vigencia_inicio TEXT,
    vigencia_fim    TEXT,
    ativo           INTEGER NOT NULL DEFAULT 1,
    criado_em       TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_cest_ncm ON cest(ncm_prefix);
"""

SEED_CSOSN = [
    ("101", "Tributada pelo Simples Nacional com permissão de crédito"),
    ("102", "Tributada pelo Simples Nacional sem permissão de crédito"),
    ("103", "Isenção do ICMS no Simples Nacional para faixa de receita bruta"),
    ("106", "Tributada pelo Simples Nacional com cobrança do ICMS por ST"),
    ("107", "Tributada pelo Simples Nacional com permissão de crédito e ICMS por ST"),
    ("201", "Tributada pelo Simples Nacional com permissão de crédito e ICMS por ST"),
    ("202", "Tributada pelo Simples Nacional sem permissão de crédito e ICMS por ST"),
    ("203", "Isenção do ICMS no Simples Nacional para faixa de receita bruta e ICMS por ST"),
    ("300", "Imune"),
    ("400", "Não tributada pelo Simples Nacional"),
    ("500", "ICMS cobrado anteriormente por ST ou por antecipação"),
    ("900", "Outros"),
]

SEED_BENEFICIOS = [
    ("ISENCAO", "Isenção de ICMS", "isencao", 0),
    ("RED_BASE", "Redução de base de cálculo ICMS", "reducao_base", 20),
    ("CRED_PRES", "Crédito presumido de ICMS", "credito_presumido", 0),
    ("DIFERIDO", "Diferimento do ICMS", "diferimento", 0),
    ("SUSPENSO", "Suspensão do ICMS", "suspensao", 0),
]


def _cols(conn: sqlite3.Connection, table: str) -> set[str]:
    return {r[1] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()}


def guard(conn: sqlite3.Connection) -> bool:
    try:
        return "origem" in _cols(conn, "fiscal_config")
    except sqlite3.OperationalError:
        return False


def forward(conn: sqlite3.Connection) -> None:
    conn.executescript(_SCHEMA)
    if not conn.execute("SELECT 1 FROM csosn LIMIT 1").fetchone():
        conn.executemany("INSERT OR IGNORE INTO csosn (codigo, descricao) VALUES (?,?)", SEED_CSOSN)
    if not conn.execute("SELECT 1 FROM beneficios_fiscais LIMIT 1").fetchone():
        conn.executemany(
            "INSERT OR IGNORE INTO beneficios_fiscais (codigo, descricao, tipo, valor_default) VALUES (?,?,?,?)",
            SEED_BENEFICIOS,
        )
    for col in _COLS_FISCAL_CONFIG:
        if col.split()[0] not in _cols(conn, "fiscal_config"):
            conn.execute(f"ALTER TABLE fiscal_config ADD COLUMN {col}")


def backward(conn: sqlite3.Connection) -> None:
    for col in _COLS_FISCAL_CONFIG:
        name = col.split()[0]
        try:
            conn.execute(f"ALTER TABLE fiscal_config DROP COLUMN {name}")
        except sqlite3.OperationalError:
            pass
    conn.executescript(
        "DROP TABLE IF EXISTS beneficios_fiscais;"
        " DROP TABLE IF EXISTS csosn;"
        " DROP TABLE IF EXISTS cest;"
    )
