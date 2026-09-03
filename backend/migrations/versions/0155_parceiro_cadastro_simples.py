"""Migração 0155 — cadastro simples de parceiro e restrição das indicações ao Admin/Financeiro."""
from __future__ import annotations

import json

VERSION = 155
RISCO = "moderada"
NAME = "parceiro_cadastro_simples"

MUDANCA = {
    "o_que": [
        "Permite cadastrar parceiro sem vínculo com cliente (cadastro simples)",
        "Adiciona nome, apelido, cpf, telefone, whatsapp e e-mail ao parceiro",
        "Restringe a visualização das indicações/parceiros a Administrador e Financeiro",
    ],
    "porque": [
        "O parceiro não precisa ser cliente: ele indica clientes e recebe pontos/bônus",
        "Evitar que pessoas estranhas ao grupo Admin/Financeiro acessem as indicações",
    ],
}


def guard(conn) -> bool:
    cols = {r[0] for r in conn.execute(
        "SELECT column_name FROM information_schema.columns "
        "WHERE table_schema='public' AND table_name='parceiro_profissional' "
        "AND column_name IN ('nome','apelido','cpf','telefone','whatsapp','email')"
    ).fetchall()}
    if len(cols) != 6:
        return False
    nullable = conn.execute(
        "SELECT is_nullable FROM information_schema.columns "
        "WHERE table_schema='public' AND table_name='parceiro_profissional' "
        "AND column_name='cliente_id'"
    ).fetchone()
    if not nullable or nullable[0] != "YES":
        return False
    vendedor = conn.execute(
        "SELECT 1 FROM perfil_recurso pr JOIN perfis p ON p.id=pr.perfil_id "
        "JOIN recursos r ON r.id=pr.recurso_id "
        "WHERE p.nome='Vendedor' AND r.codigo='parceiros' LIMIT 1"
    ).fetchone()
    financeiro = conn.execute(
        "SELECT 1 FROM perfil_recurso pr JOIN perfis p ON p.id=pr.perfil_id "
        "JOIN recursos r ON r.id=pr.recurso_id WHERE p.nome='Financeiro' AND r.codigo='parceiros' "
        "AND pr.acoes @> %s::jsonb",
        (json.dumps(["visualizar"]),),
    ).fetchone()
    return (vendedor is None) and bool(financeiro)


def forward(conn) -> None:
    conn.execute("ALTER TABLE parceiro_profissional ALTER COLUMN cliente_id DROP NOT NULL")
    conn.execute(
        "ALTER TABLE parceiro_profissional ADD COLUMN IF NOT EXISTS nome TEXT, "
        "ADD COLUMN IF NOT EXISTS apelido TEXT, ADD COLUMN IF NOT EXISTS cpf TEXT, "
        "ADD COLUMN IF NOT EXISTS telefone TEXT, ADD COLUMN IF NOT EXISTS whatsapp TEXT, "
        "ADD COLUMN IF NOT EXISTS email TEXT"
    )
    # Restrição: Vendedor não visualiza a rede/indicações de parceiros.
    conn.execute(
        "DELETE FROM perfil_recurso pr USING perfis p, recursos r "
        "WHERE p.nome='Vendedor' AND r.codigo='parceiros' "
        "AND pr.perfil_id=p.id AND pr.recurso_id=r.id"
    )
    # Financeiro: visualizar + aprovar (merge nas ações existentes).
    conn.execute(
        "INSERT INTO perfil_recurso (perfil_id, recurso_id, acoes) "
        "SELECT p.id, r.id, %s::jsonb FROM perfis p CROSS JOIN recursos r "
        "WHERE p.nome='Financeiro' AND r.codigo='parceiros' "
        "ON CONFLICT (perfil_id, recurso_id) DO UPDATE SET acoes = "
        "(SELECT jsonb_agg(DISTINCT value) FROM jsonb_array_elements_text("
        "perfil_recurso.acoes || EXCLUDED.acoes) value)",
        (json.dumps(["visualizar", "aprovar"]),),
    )
    conn.commit()


def backward(conn) -> None:
    conn.execute(
        "ALTER TABLE parceiro_profissional DROP COLUMN IF EXISTS nome, "
        "DROP COLUMN IF EXISTS apelido, DROP COLUMN IF EXISTS cpf, "
        "DROP COLUMN IF EXISTS telefone, DROP COLUMN IF EXISTS whatsapp, "
        "DROP COLUMN IF EXISTS email"
    )
    # cliente_id volta a ser NOT NULL apenas se não houver parceiro sem cliente.
    nulos = conn.execute(
        "SELECT COUNT(*) FROM parceiro_profissional WHERE cliente_id IS NULL"
    ).fetchone()[0]
    if nulos == 0:
        conn.execute("ALTER TABLE parceiro_profissional ALTER COLUMN cliente_id SET NOT NULL")
    conn.execute(
        "INSERT INTO perfil_recurso (perfil_id, recurso_id, acoes) "
        "SELECT p.id, r.id, %s::jsonb FROM perfis p CROSS JOIN recursos r "
        "WHERE p.nome='Vendedor' AND r.codigo='parceiros' "
        "ON CONFLICT (perfil_id, recurso_id) DO NOTHING",
        (json.dumps(["visualizar", "cadastrar", "editar"]),),
    )
    conn.commit()