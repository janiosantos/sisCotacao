"""Operacoes controladas de manutencao de usuarios.

Este modulo e executado pelo runner de producao a partir do checkout, usando o
runtime do container backend ativo. Senhas entram exclusivamente por variavel
de ambiente e nunca sao gravadas em logs ou eventos de auditoria.
"""
from __future__ import annotations

import os
import sys

from werkzeug.security import generate_password_hash

from catalog_server.db import system_conn
from catalog_server.services import infra


TEST_LOGIN = "teste"
TEST_NAME = "Usuario de Teste"
TEST_PROFILE = "Vendedor"
PASSWORD_ENV = "SISCOM_MAINTENANCE_PASSWORD"


def provision_test_user(conn, password: str) -> dict:
    """Cria a conta de teste de menor privilegio em uma unica transacao."""
    if len(password) < 8:
        raise ValueError("A senha de manutencao deve possuir pelo menos 8 caracteres")

    conn.execute(
        "SELECT pg_advisory_xact_lock(hashtext(?))",
        (f"maintenance-user:{TEST_LOGIN}",),
    )
    profile = conn.execute(
        "SELECT id FROM perfis WHERE nome=? AND ativo=1",
        (TEST_PROFILE,),
    ).fetchone()
    if not profile:
        raise RuntimeError(f"Perfil ativo {TEST_PROFILE!r} nao encontrado")

    existing = conn.execute(
        "SELECT id FROM usuarios WHERE lower(login)=lower(?)",
        (TEST_LOGIN,),
    ).fetchone()
    if existing:
        raise RuntimeError(
            f"O login {TEST_LOGIN!r} ja existe; nenhuma credencial foi alterada"
        )

    row = conn.execute(
        "INSERT INTO usuarios "
        "(nome, login, senha_hash, ativo, desconto_limite_pct, autoriza_desconto) "
        "VALUES (?,?,?,?,?,?) RETURNING id",
        (
            TEST_NAME,
            TEST_LOGIN,
            generate_password_hash(password),
            1,
            0,
            0,
        ),
    ).fetchone()
    user_id = int(row["id"])
    conn.execute(
        "INSERT INTO usuario_perfis (usuario_id, perfil_id) VALUES (?,?)",
        (user_id, int(profile["id"])),
    )
    infra.registrar(
        "usuario_teste_criado",
        alvo_tipo="usuario",
        alvo_id=user_id,
        depois={
            "login": TEST_LOGIN,
            "nome": TEST_NAME,
            "perfil": TEST_PROFILE,
            "ativo": True,
        },
        motivo="Diagnostico controlado de autenticacao em producao",
        ator_login="maintenance-runner",
        conn=conn,
    )
    return {"id": user_id, "login": TEST_LOGIN, "perfil": TEST_PROFILE}


def main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    if args != ["create-test-user"]:
        print("Operacao disponivel: create-test-user", file=sys.stderr)
        return 2

    password = os.getenv(PASSWORD_ENV, "")
    if not password:
        print(f"ERRO: secret {PASSWORD_ENV} ausente", file=sys.stderr)
        return 2

    try:
        with system_conn() as conn:
            result = provision_test_user(conn, password)
    except (RuntimeError, ValueError) as exc:
        print(f"ERRO: {exc}", file=sys.stderr)
        return 1

    print(
        "Usuario criado e auditado: "
        f"id={result['id']} login={result['login']} perfil={result['perfil']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
