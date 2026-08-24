"""Migração 0077 — Contract: remove a coluna legada `usuarios.perfil`.

O RBAC (migração 0075) já é a fonte única de perfis via `usuario_perfis`.
Esta migração:
1. Backfill idempotente: usuário sem relação `usuario_perfis` entra no perfil
   correspondente ao legado (admin → Administrador, senão → Vendedor);
2. Remove a coluna `usuarios.perfil` (destrutiva — Contract, etapa F).

Código já atualizado na mesma release para não depender da coluna.
"""
from __future__ import annotations

VERSION = 77
RISCO = "critica"
NAME = "rbac_contract_perfil"

MUDANCA = {
    "o_que": [
        "Backfill: usuários órfãos de RBAC ganham perfil derivado do legado",
        "Remove a coluna usuarios.perfil (legado admin/vendedor)",
    ],
    "porque": [
        "RBAC via usuario_perfis é a fonte única; eliminar dupla fonte (Contract)"
    ],
}


def guard(conn) -> bool:
    row = conn.execute(
        "SELECT 1 FROM information_schema.columns"
        " WHERE table_name='usuarios' AND column_name='perfil'"
    ).fetchone()
    return row is None


def forward(conn) -> None:
    ac = conn.autocommit
    conn.autocommit = True
    try:
        # Backfill idempotente de usuários órfãos (antes do DROP).
        for row in conn.execute(
            "SELECT u.id, u.perfil FROM usuarios u"
            " WHERE NOT EXISTS (SELECT 1 FROM usuario_perfis up"
            "   WHERE up.usuario_id = u.id)"
        ).fetchall():
            nome_perfil = "Administrador" if row[1] == "admin" else "Vendedor"
            pid = conn.execute(
                "SELECT id FROM perfis WHERE nome=%s", (nome_perfil,)
            ).fetchone()
            if pid is None:
                continue
            conn.execute(
                "INSERT INTO usuario_perfis (usuario_id, perfil_id)"
                " VALUES (%s, %s) ON CONFLICT DO NOTHING",
                (row[0], pid[0]),
            )
        conn.execute("ALTER TABLE usuarios DROP COLUMN IF EXISTS perfil")
    finally:
        conn.autocommit = ac


def backward(conn) -> None:
    ac = conn.autocommit
    conn.autocommit = True
    try:
        conn.execute(
            "ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS perfil"
            " TEXT NOT NULL DEFAULT 'vendedor'"
        )
        # Reconstrói o legado a partir do RBAC (melhor esforço).
        conn.execute(
            """
            UPDATE usuarios u SET perfil = CASE
                WHEN EXISTS (SELECT 1 FROM usuario_perfis up
                             JOIN perfis p ON p.id=up.perfil_id
                             WHERE up.usuario_id=u.id AND p.nome='Administrador')
                THEN 'admin' ELSE 'vendedor' END
            """
        )
    finally:
        conn.autocommit = ac