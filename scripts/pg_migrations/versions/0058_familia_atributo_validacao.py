"""Migração 0058 — Validação de atributos livres.

Adiciona `familia_atributos.validacao`: regra de validação para atributos do
tipo "livre" (valor digitado no cadastro do produto):
  - `texto`          : qualquer texto (padrão).
  - `numero`         : apenas números (inteiro ou decimal).
  - `alphanumerico`  : letras e números (sem símbolos).
"""
from __future__ import annotations

VERSION = 58
RISCO = "melhoria"

# Documentação da mudança de banco (exigida pelo runner desde a v1.6.2).
MUDANCA = {
    "o_que": ["Adiciona familia_atributos.validacao (texto|numero|alphanumerico)"],
    "porque": ["Validar valores digitados de atributos livres no cadastro de produtos"],
}
NAME = "familia_atributo_validacao"


def guard(conn) -> bool:
    row = conn.execute(
        "SELECT 1 FROM information_schema.columns"
        " WHERE table_name='familia_atributos' AND column_name='validacao'"
    ).fetchone()
    return row is not None


def forward(conn) -> None:
    autocommit = conn.autocommit
    conn.autocommit = True
    try:
        conn.execute(
            "ALTER TABLE familia_atributos ADD COLUMN validacao TEXT DEFAULT 'texto'"
        )
    finally:
        conn.autocommit = autocommit


def backward(conn) -> None:
    autocommit = conn.autocommit
    conn.autocommit = True
    try:
        conn.execute("ALTER TABLE familia_atributos DROP COLUMN IF EXISTS validacao")
    finally:
        conn.autocommit = autocommit
