"""0039 - Histórico da configuração fiscal (auditoria).

`fiscal_config_historico` guarda um snapshot da `fiscal_config` a cada criação
ou atualização: quem (usuário da sessão) e quando, com a vigência das regras.
Complementa `preco_historico` (migração 0038) na auditoria do fluxo
Fiscal → Custo → Precificação.
"""
from __future__ import annotations

import sqlite3

VERSION = 39
NAME = "Histórico da configuração fiscal (auditoria)"

_SQL = """
CREATE TABLE IF NOT EXISTS fiscal_config_historico (
    id                      INTEGER PRIMARY KEY AUTOINCREMENT,
    variante_id             INTEGER NOT NULL REFERENCES variantes(id),
    tipo                    TEXT NOT NULL DEFAULT 'atualizado'
                            CHECK(tipo IN ('criado','atualizado')),
    ncm                     TEXT DEFAULT '',
    cfop                    TEXT,
    cst_icms                TEXT,
    cst_pis                 TEXT,
    cst_cofins              TEXT,
    aliquota_icms           REAL DEFAULT 0,
    aliquota_pis            REAL DEFAULT 0,
    aliquota_cofins         REAL DEFAULT 0,
    aliquota_ipi            REAL DEFAULT 0,
    origem                  INTEGER DEFAULT 0,
    cest                    TEXT DEFAULT '',
    csosn                   TEXT DEFAULT '',
    aliquota_icms_st        REAL DEFAULT 0,
    mva                     REAL DEFAULT 0,
    base_reducao            REAL DEFAULT 0,
    aliquota_interestadual  REAL DEFAULT 0,
    aliquota_fecp           REAL DEFAULT 0,
    credito_icms            REAL DEFAULT 0,
    beneficio_id            INTEGER,
    vigencia_inicio         TEXT,
    vigencia_fim            TEXT,
    usuario_id              INTEGER REFERENCES usuarios(id),
    criado_em               TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_fisc_hist_var ON fiscal_config_historico(variante_id);
CREATE INDEX IF NOT EXISTS idx_fisc_hist_data ON fiscal_config_historico(criado_em);
"""


def guard(conn: sqlite3.Connection) -> bool:
    try:
        conn.execute("SELECT 1 FROM fiscal_config_historico LIMIT 1").fetchone()
    except sqlite3.OperationalError:
        return False
    return True


def forward(conn: sqlite3.Connection) -> None:
    conn.executescript(_SQL)


def backward(conn: sqlite3.Connection) -> None:
    conn.execute("DROP TABLE IF EXISTS fiscal_config_historico")
