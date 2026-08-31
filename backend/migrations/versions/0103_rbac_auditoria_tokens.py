"""Migração 0103 — auditoria RBAC e revogação de tokens.

Expand-only: adiciona versão por usuário para invalidar tokens emitidos e uma
trilha append-only das alterações administrativas do RBAC.
"""
from __future__ import annotations

VERSION = 103
RISCO = "moderada"
NAME = "rbac_auditoria_tokens"

MUDANCA = {
    "o_que": [
        "Adiciona usuarios.token_version para revogar tokens sem estado no cliente",
        "Cria rbac_audit_log para registrar alterações de perfis e permissões",
    ],
    "porque": [
        "Logout e troca de senha precisam invalidar tokens já emitidos",
        "Alterações de acesso administrativo precisam ser rastreáveis",
    ],
}


def guard(conn) -> bool:
    column = conn.execute(
        "SELECT 1 FROM information_schema.columns "
        "WHERE table_schema='public' AND table_name='usuarios' "
        "AND column_name='token_version'"
    ).fetchone()
    table = conn.execute(
        "SELECT 1 FROM information_schema.tables "
        "WHERE table_schema='public' AND table_name='rbac_audit_log'"
    ).fetchone()
    return bool(column and table)


def forward(conn) -> None:
    conn.execute(
        "ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS "
        "token_version INTEGER NOT NULL DEFAULT 0"
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS rbac_audit_log (
            id BIGSERIAL PRIMARY KEY,
            actor_usuario_id BIGINT REFERENCES usuarios(id) ON DELETE SET NULL,
            target_usuario_id BIGINT REFERENCES usuarios(id) ON DELETE SET NULL,
            target_perfil_id BIGINT REFERENCES perfis(id) ON DELETE SET NULL,
            operacao TEXT NOT NULL,
            recurso TEXT,
            antes JSONB,
            depois JSONB,
            motivo TEXT NOT NULL DEFAULT '',
            ip TEXT,
            criado_em TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_rbac_audit_criado "
        "ON rbac_audit_log (criado_em DESC)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_rbac_audit_target "
        "ON rbac_audit_log (target_usuario_id, criado_em DESC)"
    )
    conn.commit()


def backward(conn) -> None:
    conn.execute("DROP TABLE IF EXISTS rbac_audit_log")
    conn.execute("ALTER TABLE usuarios DROP COLUMN IF EXISTS token_version")
    conn.commit()
