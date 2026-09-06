from __future__ import annotations

from werkzeug.security import check_password_hash

from catalog_server import maintenance_users


def _create_admin(conn, password: str = "senha-anterior") -> int:
    from werkzeug.security import generate_password_hash

    row = conn.execute(
        "INSERT INTO usuarios (nome, login, senha_hash, token_version) "
        "VALUES (?,?,?,?) RETURNING id",
        ("Administrador", "admin", generate_password_hash(password), 3),
    ).fetchone()
    conn.execute(
        "INSERT INTO usuario_perfis (usuario_id, perfil_id) "
        "SELECT ?, id FROM perfis WHERE nome='Administrador'",
        (int(row["id"]),),
    )
    return int(row["id"])


def test_provision_test_user_creates_vendedor_and_audit(conn):
    password = "senha-segura-123"

    result = maintenance_users.provision_test_user(conn, password)

    user = conn.execute(
        "SELECT id, login, senha_hash, ativo, desconto_limite_pct, autoriza_desconto "
        "FROM usuarios WHERE id=?",
        (result["id"],),
    ).fetchone()
    assert user["login"] == "teste"
    assert user["ativo"] == 1
    assert float(user["desconto_limite_pct"]) == 0
    assert user["autoriza_desconto"] == 0
    assert check_password_hash(user["senha_hash"], password)

    profile = conn.execute(
        "SELECT p.nome FROM usuario_perfis up "
        "JOIN perfis p ON p.id=up.perfil_id WHERE up.usuario_id=?",
        (result["id"],),
    ).fetchone()
    assert profile["nome"] == "Vendedor"

    audit = conn.execute(
        "SELECT ator_login, acao, depois FROM auditoria_evento "
        "WHERE alvo_tipo='usuario' AND alvo_id=?",
        (str(result["id"]),),
    ).fetchone()
    assert audit["ator_login"] == "maintenance-runner"
    assert audit["acao"] == "usuario_teste_criado"
    assert password not in str(audit["depois"])
    assert user["senha_hash"] not in str(audit["depois"])


def test_provision_test_user_does_not_replace_existing_login(conn):
    maintenance_users.provision_test_user(conn, "primeira-senha")

    try:
        maintenance_users.provision_test_user(conn, "segunda-senha")
    except RuntimeError as exc:
        assert "ja existe" in str(exc)
    else:
        raise AssertionError("A conta existente nao poderia ser sobrescrita")

    user = conn.execute(
        "SELECT senha_hash FROM usuarios WHERE login='teste'"
    ).fetchone()
    assert check_password_hash(user["senha_hash"], "primeira-senha")
    assert not check_password_hash(user["senha_hash"], "segunda-senha")


def test_reset_admin_password_revokes_tokens_and_keeps_rbac(conn):
    admin_id = _create_admin(conn)
    new_password = "nova-senha-segura"

    result = maintenance_users.reset_admin_password(conn, new_password)

    admin = conn.execute(
        "SELECT senha_hash, token_version, ativo FROM usuarios WHERE id=?",
        (admin_id,),
    ).fetchone()
    assert result["id"] == admin_id
    assert admin["ativo"] == 1
    assert admin["token_version"] == 4
    assert check_password_hash(admin["senha_hash"], new_password)
    assert not check_password_hash(admin["senha_hash"], "senha-anterior")

    profile = conn.execute(
        "SELECT p.nome FROM usuario_perfis up "
        "JOIN perfis p ON p.id=up.perfil_id WHERE up.usuario_id=?",
        (admin_id,),
    ).fetchone()
    assert profile["nome"] == "Administrador"

    audit = conn.execute(
        "SELECT antes, depois FROM auditoria_evento "
        "WHERE acao='senha_admin_redefinida' AND alvo_id=?",
        (str(admin_id),),
    ).fetchone()
    assert audit is not None
    assert new_password not in str(audit)
    assert admin["senha_hash"] not in str(audit)


def test_reset_admin_password_rejects_login_without_admin_profile(conn):
    row = conn.execute(
        "INSERT INTO usuarios (nome, login, senha_hash) "
        "VALUES ('Admin sem perfil','admin','hash-antigo') RETURNING id"
    ).fetchone()
    conn.execute(
        "INSERT INTO usuario_perfis (usuario_id, perfil_id) "
        "SELECT ?, id FROM perfis WHERE nome='Vendedor'",
        (int(row["id"]),),
    )

    try:
        maintenance_users.reset_admin_password(conn, "nova-senha-segura")
    except RuntimeError as exc:
        assert "perfil Administrador" in str(exc)
    else:
        raise AssertionError("Login sem perfil Administrador nao poderia ser alterado")

    stored = conn.execute(
        "SELECT senha_hash, token_version FROM usuarios WHERE id=?",
        (int(row["id"]),),
    ).fetchone()
    assert stored["senha_hash"] == "hash-antigo"
    assert stored["token_version"] == 0
