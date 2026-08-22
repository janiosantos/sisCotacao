"""Migração 0062 — Notas de release no log de atualizações.

Adiciona a `sistema_atualizacoes` os campos do manifesto de release
(`releases/vX.Y.Z.json`): versão da release, componentes afetados e as listas
de correções / melhorias / recursos. Alimenta o Histórico do Painel de
Atualizações com o registro do QUE mudou, não apenas das versões.
"""
from __future__ import annotations

VERSION = 62
RISCO = "rotina"

# Documentação da mudança de banco (exigida pelo runner desde a v1.6.2).
MUDANCA = {
    "o_que": [
        "Adiciona versao_release/componentes/correcoes/melhorias/recursos em sistema_atualizacoes",
    ],
    "porque": ["Registrar O QUE mudou por release (notas do manifesto), não apenas versões"],
}
NAME = "notas_release"

_COLUNAS = (
    "versao_release TEXT",
    "componentes JSONB",
    "correcoes JSONB",
    "melhorias JSONB",
    "recursos JSONB",
)


def guard(conn) -> bool:
    row = conn.execute(
        "SELECT 1 FROM information_schema.columns"
        " WHERE table_name='sistema_atualizacoes' AND column_name='versao_release'"
    ).fetchone()
    return row is not None


def forward(conn) -> None:
    autocommit = conn.autocommit
    conn.autocommit = True
    try:
        for col in _COLUNAS:
            conn.execute(
                f"ALTER TABLE sistema_atualizacoes ADD COLUMN IF NOT EXISTS {col}"
            )
    finally:
        conn.autocommit = autocommit


def backward(conn) -> None:
    autocommit = conn.autocommit
    conn.autocommit = True
    try:
        for col in _COLUNAS:
            nome = col.split()[0]
            conn.execute(
                f"ALTER TABLE sistema_atualizacoes DROP COLUMN IF EXISTS {nome}"
            )
    finally:
        conn.autocommit = autocommit
