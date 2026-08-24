"""Migração 0076 — Negação por usuário no RBAC.

`usuario_override` ganha `acoes_negadas` (JSONB): ações que o usuário NÃO pode
executar num recurso mesmo quando um perfil concede. A efetiva é
`(perfis ∪ acoes_extra) − acoes_negadas`. Superuser (Administrador) ignora
negações.

Expand: aditivo, sem remover nada.
"""
from __future__ import annotations

VERSION = 76
RISCO = "rotina"
NAME = "rbac_negacao_usuario"

MUDANCA = {
    "o_que": [
        "Adiciona acoes_negadas (JSONB) em usuario_override para negação por usuário",
    ],
    "porque": [
        "Permitir negar ações pontuais por usuário (a efetiva é perfis+conceder−negar; superuser ignora)"
    ],
}


def guard(conn) -> bool:
    row = conn.execute(
        "SELECT 1 FROM information_schema.columns"
        " WHERE table_name='usuario_override' AND column_name='acoes_negadas'"
    ).fetchone()
    return row is not None


def forward(conn) -> None:
    ac = conn.autocommit
    conn.autocommit = True
    try:
        conn.execute(
            "ALTER TABLE usuario_override"
            " ADD COLUMN IF NOT EXISTS acoes_negadas JSONB NOT NULL DEFAULT '[]'"
        )
    finally:
        conn.autocommit = ac


def backward(conn) -> None:
    ac = conn.autocommit
    conn.autocommit = True
    try:
        conn.execute(
            "ALTER TABLE usuario_override DROP COLUMN IF EXISTS acoes_negadas"
        )
    finally:
        conn.autocommit = ac