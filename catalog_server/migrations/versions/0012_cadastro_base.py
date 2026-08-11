"""0012 — Cadastro base do ERP comercial (Fase 1).

Tabelas de pessoas/orgação para o fluxo comercial (inspirado nos artigos
"Usuários", "Cadastro de clientes", "Vendedores" e "Plano de contas" da doc
do Bravo Gestor):

- `usuarios`      → quem acessa o sistema (login/senha/perfil).
- `vendedores`    → vendedores da empresa (comissão e ativo).
- `clientes`      → clientes (pessoa física/jurídica) vinculados a vendedores.
- `plano_de_contas` → estrutura de contas para classificar receitas/despesas.
"""
from __future__ import annotations

import sqlite3

VERSION = 12
NAME = "Cadastro base do ERP: usuarios, vendedores, clientes e plano de contas"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS usuarios (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    nome        TEXT NOT NULL,
    login       TEXT NOT NULL UNIQUE,
    senha_hash  TEXT NOT NULL,
    perfil      TEXT NOT NULL DEFAULT 'vendedor',
    ativo       INTEGER NOT NULL DEFAULT 1,
    criado_em   TEXT NOT NULL DEFAULT (datetime('now')),
    atualizado_em TEXT
);

CREATE TABLE IF NOT EXISTS vendedores (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    nome          TEXT NOT NULL,
    comissao_pct  REAL NOT NULL DEFAULT 0,
    ativo         INTEGER NOT NULL DEFAULT 1,
    criado_em     TEXT NOT NULL DEFAULT (datetime('now')),
    atualizado_em TEXT
);

CREATE TABLE IF NOT EXISTS clientes (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    nome           TEXT NOT NULL,
    tipo_pessoa    TEXT NOT NULL DEFAULT 'f',
    doc            TEXT,
    email          TEXT,
    telefone       TEXT,
    whatsapp       TEXT,
    endereco       TEXT,
    cidade         TEXT,
    uf             TEXT,
    cep            TEXT,
    vendedor_id    INTEGER REFERENCES vendedores(id) ON DELETE SET NULL,
    limite_credito REAL NOT NULL DEFAULT 0,
    observacoes    TEXT,
    ativo          INTEGER NOT NULL DEFAULT 1,
    criado_em      TEXT NOT NULL DEFAULT (datetime('now')),
    atualizado_em  TEXT
);

CREATE INDEX IF NOT EXISTS idx_clientes_vendedor ON clientes(vendedor_id);
CREATE INDEX IF NOT EXISTS idx_clientes_doc ON clientes(doc);
CREATE INDEX IF NOT EXISTS idx_clientes_nome ON clientes(nome);

CREATE TABLE IF NOT EXISTS plano_de_contas (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    codigo     TEXT NOT NULL,
    nome       TEXT NOT NULL,
    tipo       TEXT NOT NULL DEFAULT 'receita',
    pai_id     INTEGER REFERENCES plano_de_contas(id) ON DELETE CASCADE,
    ativo      INTEGER NOT NULL DEFAULT 1,
    criado_em  TEXT NOT NULL DEFAULT (datetime('now')),
    atualizado_em TEXT
);

CREATE INDEX IF NOT EXISTS idx_plano_contas_pai ON plano_de_contas(pai_id);
"""


def guard(conn: sqlite3.Connection) -> bool:
    try:
        conn.execute("SELECT 1 FROM usuarios LIMIT 1").fetchone()
        conn.execute("SELECT 1 FROM vendedores LIMIT 1").fetchone()
        conn.execute("SELECT 1 FROM clientes LIMIT 1").fetchone()
        conn.execute("SELECT 1 FROM plano_de_contas LIMIT 1").fetchone()
    except sqlite3.OperationalError:
        return False
    return True


def forward(conn: sqlite3.Connection) -> None:
    conn.executescript(_SCHEMA)
    # Usuário administrador inicial (só quando o sistema ainda não tem ninguém,
    # para o primeiro acesso ser possível). Troque a senha pelo sistema.
    if not conn.execute("SELECT 1 FROM usuarios LIMIT 1").fetchone():
        from werkzeug.security import generate_password_hash

        conn.execute(
            "INSERT INTO usuarios (nome, login, senha_hash, perfil)"
            " VALUES (?,?,?,?)",
            ("Administrador", "admin", generate_password_hash("admin123"), "admin"),
        )


def backward(conn: sqlite3.Connection) -> None:
    conn.executescript(
        "DROP TABLE IF EXISTS plano_de_contas;"
        " DROP TABLE IF EXISTS clientes;"
        " DROP TABLE IF EXISTS vendedores;"
        " DROP TABLE IF EXISTS usuarios;"
    )