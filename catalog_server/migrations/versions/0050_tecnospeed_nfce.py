"""
0050 — Emissão de NFC-e/NF-e via Tecnospeed.

- `documentos_fiscais` → uma linha por tentativa de emissão de NFC-e (modelo
  65) ou NF-e (modelo 55) atrelada a um orçamento faturado. Guarda o ciclo
  de vida completo (pendente → processando → autorizado/rejeitado/cancelado)
  e os dados de retorno da SEFAZ repassados pela Tecnospeed (chave de
  acesso, protocolo, XML e DANFE/DANFCE).
- `tecnospeed_config` → credenciais e ambiente da integração (chave/valor,
  mesmo padrão de `config_loja`), separada por ser dado sensível (token).

ATENÇÃO: esta migração cria a estrutura de rastreio; a integração de fato
com a API da Tecnospeed (client HTTP) está em
`catalog_server/services/tecnospeed.py`, e por padrão roda em modo
simulação até alguém configurar token/CNPJ reais — ver `TECNOSPEED.md`.
"""
from __future__ import annotations

import sqlite3

VERSION = 50
NAME = "Documentos fiscais (NFC-e/NF-e) + config Tecnospeed"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS documentos_fiscais (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    orcamento_id      INTEGER NOT NULL REFERENCES orcamentos(id) ON DELETE CASCADE,
    modelo            TEXT NOT NULL DEFAULT '65' CHECK(modelo IN ('55','65')),
    ambiente          TEXT NOT NULL DEFAULT 'homologacao' CHECK(ambiente IN ('homologacao','producao')),
    status            TEXT NOT NULL DEFAULT 'pendente'
                      CHECK(status IN ('pendente','processando','autorizado','rejeitado','cancelado','erro')),
    tecnospeed_id     TEXT,
    chave_acesso      TEXT,
    protocolo         TEXT,
    numero            INTEGER,
    serie             INTEGER,
    motivo            TEXT,
    xml_url           TEXT,
    danfe_url         TEXT,
    payload_enviado   TEXT,
    resposta_bruta    TEXT,
    criado_em         TEXT NOT NULL DEFAULT (datetime('now')),
    atualizado_em     TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(orcamento_id, modelo)
);

CREATE INDEX IF NOT EXISTS idx_docfiscal_orc ON documentos_fiscais(orcamento_id);
CREATE INDEX IF NOT EXISTS idx_docfiscal_status ON documentos_fiscais(status);
CREATE INDEX IF NOT EXISTS idx_docfiscal_tecnospeed ON documentos_fiscais(tecnospeed_id);

CREATE TABLE IF NOT EXISTS tecnospeed_config (
    chave         TEXT PRIMARY KEY,
    valor         TEXT NOT NULL DEFAULT '',
    atualizado_em TEXT NOT NULL DEFAULT (datetime('now'))
);
"""

SEED_CONFIG = [
    ("ambiente", "homologacao"),
    ("simulado", "1"),  # 1 = não chama a API real; usado até alguém configurar credenciais
    ("token", ""),
    ("cnpj_emitente", ""),
    ("serie_nfce", "1"),
    ("serie_nfe", "1"),
]


def guard(conn: sqlite3.Connection) -> bool:
    try:
        conn.execute("SELECT 1 FROM documentos_fiscais LIMIT 1").fetchone()
        conn.execute("SELECT 1 FROM tecnospeed_config LIMIT 1").fetchone()
    except sqlite3.OperationalError:
        return False
    return True


def forward(conn: sqlite3.Connection) -> None:
    conn.executescript(_SCHEMA)
    for chave, valor in SEED_CONFIG:
        conn.execute(
            "INSERT OR IGNORE INTO tecnospeed_config (chave, valor) VALUES (?,?)",
            (chave, valor),
        )


def backward(conn: sqlite3.Connection) -> None:
    conn.executescript(
        "DROP TABLE IF EXISTS documentos_fiscais;"
        " DROP TABLE IF EXISTS tecnospeed_config;"
    )
