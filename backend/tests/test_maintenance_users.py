from __future__ import annotations

from werkzeug.security import check_password_hash

from catalog_server import maintenance_users


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
