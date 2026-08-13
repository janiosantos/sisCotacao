"""0042 - Modelagem fiscal: matriz de regras, versão e auditoria.

Módulo Fiscal — núcleo do mecanismo de regras:

- `fiscal_regra`          : matriz parametrizada. Cada linha é uma regra que casa
  um CONTEXTO (regime, UF origem/destino, tipo de cliente, condição de
  contribuinte, finalidade, modelo de documento, natureza, NCM/CEST/origem) e
  prescreve o RESULTADO fiscal (CFOP, CST/CSOSN, PIS/COFINS, IBS/CBS, ICMS/ST).

  Critérios vazios ('') significam "qualquer valor". `prioridade` menor vence.
  IMPORTANTE: nenhum código/alíquota é inventado aqui; a matriz é populada
  somente com regras confirmadas/parametrizadas.

- `fiscal_regra_versao`   : versionamento com vigência (data_inicio/data_fim),
  fonte normativa, status. O motor escolhe a versão válida na data da operação.

- `fiscal_regra_auditoria`: registro de quem/quando/o que mudou (valor anterior,
  novo, motivo, fonte, vigência) — sem alteração silenciosa.
"""
from __future__ import annotations

import sqlite3

VERSION = 42
NAME = "Modelagem fiscal: matriz de regras, versão e auditoria"

_SQL = """
CREATE TABLE IF NOT EXISTS fiscal_regra (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    nome               TEXT NOT NULL,
    descricao          TEXT DEFAULT '',
    ativo              INTEGER NOT NULL DEFAULT 1,
    -- Critérios de correspondência ('' = qualquer)
    regime             TEXT DEFAULT '',
    uf_origem          TEXT DEFAULT '',
    uf_destino         TEXT DEFAULT '',
    tipo_cliente       TEXT DEFAULT '',
    contribuinte       TEXT DEFAULT '',
    finalidade         TEXT DEFAULT '',
    modelo_documento   TEXT DEFAULT '',
    natureza_operacao  TEXT DEFAULT '',
    ncm_prefixo        TEXT DEFAULT '',
    cest               TEXT DEFAULT '',
    origem             TEXT DEFAULT '',
    -- Resultado prescrito pela regra
    cfop               TEXT DEFAULT '',
    cst_icms           TEXT DEFAULT '',
    csosn              TEXT DEFAULT '',
    cst_pis            TEXT DEFAULT '',
    cst_cofins         TEXT DEFAULT '',
    cst_ibs            TEXT DEFAULT '',
    cst_cbs            TEXT DEFAULT '',
    modalidade_st      TEXT DEFAULT '',
    aliquota_icms      REAL,
    mva                REAL,
    base_reducao       REAL,
    aliquota_icms_st   REAL,
    aliquota_pis       REAL,
    aliquota_cofins    REAL,
    aliquota_ibs       REAL,
    aliquota_cbs       REAL,
    prioridade         INTEGER NOT NULL DEFAULT 100,
    observacao         TEXT DEFAULT '',
    criado_em          TEXT NOT NULL DEFAULT (datetime('now')),
    atualizado_em      TEXT
);

CREATE INDEX IF NOT EXISTS idx_fiscal_regra_ativo ON fiscal_regra(ativo);
CREATE INDEX IF NOT EXISTS idx_fiscal_regra_regime ON fiscal_regra(regime);

CREATE TABLE IF NOT EXISTS fiscal_regra_versao (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    regra_id      INTEGER NOT NULL REFERENCES fiscal_regra(id) ON DELETE CASCADE,
    versao        TEXT NOT NULL,
    fonte         TEXT DEFAULT '',
    data_inicio   TEXT NOT NULL,
    data_fim      TEXT,
    parametros    TEXT DEFAULT '{}',
    status        TEXT NOT NULL DEFAULT 'ativa'
                  CHECK(status IN ('ativa','inativa','rascunho')),
    criado_em     TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_fiscal_versao_regra ON fiscal_regra_versao(regra_id);

CREATE TABLE IF NOT EXISTS fiscal_regra_auditoria (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    regra_id        INTEGER REFERENCES fiscal_regra(id) ON DELETE SET NULL,
    acao            TEXT NOT NULL
                    CHECK(acao IN ('criada','alterada','desativada','ativada','versao')),
    usuario_id      INTEGER REFERENCES usuarios(id),
    valor_anterior  TEXT,
    valor_novo      TEXT,
    motivo          TEXT DEFAULT '',
    fonte           TEXT DEFAULT '',
    vigencia_inicio TEXT,
    vigencia_fim    TEXT,
    criado_em       TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_fiscal_audit_regra ON fiscal_regra_auditoria(regra_id);
"""


def guard(conn: sqlite3.Connection) -> bool:
    try:
        conn.execute("SELECT 1 FROM fiscal_regra LIMIT 1").fetchone()
        conn.execute("SELECT 1 FROM fiscal_regra_versao LIMIT 1").fetchone()
        conn.execute("SELECT 1 FROM fiscal_regra_auditoria LIMIT 1").fetchone()
    except sqlite3.OperationalError:
        return False
    return True


def forward(conn: sqlite3.Connection) -> None:
    conn.executescript(_SQL)


def backward(conn: sqlite3.Connection) -> None:
    conn.executescript(
        "DROP TABLE IF EXISTS fiscal_regra_auditoria;"
        " DROP TABLE IF EXISTS fiscal_regra_versao;"
        " DROP TABLE IF EXISTS fiscal_regra;"
    )
