"""Busca rápida do PDV (VEN-002): rankeada, exata antes de textual, com disponibilidade."""
from __future__ import annotations

from catalog_server import auth_token, permissao
from catalog_server.app_factory import create_app
from catalog_server.db import system_conn
from catalog_server.repositories import catalog_repo, estoque_repo


def _usuario(login: str) -> int:
    from werkzeug.security import generate_password_hash

    with system_conn() as conn:
        cur = conn.execute(
            "INSERT INTO usuarios (nome, login, senha_hash) VALUES (%s,%s,%s)",
            ("Op", login, generate_password_hash("x")),
        )
        uid = int(cur.lastrowid)
        conn.commit()
    return uid


def _setup(system_db) -> tuple[int, int, int]:
    with system_conn() as conn:
        conn.execute("INSERT INTO produtos_cadastro (nome, ativo, sku, ean, preco, marca) VALUES (%s,%s,%s,%s,%s,%s)", ("Cabo Flexível", 1, "CF-25", "7891000000001", 10.0, "Marca X"))
        pid = int(conn.execute("SELECT lastval()").fetchone()["lastval"])
        conn.execute("INSERT INTO produto_identificador (produto_id, tipo, valor) VALUES (%s,%s,%s)", (pid, "fornecedor", "FORN-123"))
        did = int(conn.execute("SELECT id FROM depositos ORDER BY id LIMIT 1").fetchone()["id"])
        conn.commit()
    estoque_repo.movimentar_fato(did, pid, "entrada", 10, origem_tipo="teste")
    return pid, did, 0


def test_exata_rankeada_primeiro(system_db):
    pid, did, _ = _setup(system_db)
    r = catalog_repo.busca_rapida("7891000000001", deposito_id=did)
    assert r[0]["id"] == pid
    assert r[0]["rank"] == 0
    r2 = catalog_repo.busca_rapida("FORN-123", deposito_id=did)
    assert r2[0]["id"] == pid
    assert r2[0]["rank"] == 1  # código fornecedor


def test_termo_textual(system_db):
    pid, did, _ = _setup(system_db)
    r = catalog_repo.busca_rapida("cabo flexivel", deposito_id=did)
    assert r and r[0]["id"] == pid
    assert r[0]["rank"] == 3


def test_disponibilidade(system_db):
    pid, did, _ = _setup(system_db)
    r = catalog_repo.busca_rapida("CF-25", deposito_id=did)
    assert r[0]["disponibilidade"]["fisico"] == 10.0
    assert r[0]["disponivel"] == 10.0
    # sem depósito → sem disponibilidade
    r2 = catalog_repo.busca_rapida("CF-25")
    assert r2[0]["disponibilidade"] is None


def test_vazio(system_db):
    _setup(system_db)
    assert catalog_repo.busca_rapida("") == []


def test_api_busca_rapida(system_db):
    pid, did, _ = _setup(system_db)
    uid = _usuario("bus_api")
    with system_conn() as conn:
        conn.execute(
            "INSERT INTO usuario_perfis (usuario_id, perfil_id) SELECT %s, id FROM perfis WHERE nome='Administrador'",
            (uid,),
        )
        conn.commit()
    permissao.invalidar(uid)
    client = create_app().test_client()
    h = {"Authorization": f"Bearer {auth_token.criar_token({'id': uid, 'login': 'bus_api'})}"}
    r = client.get(f"/api/produtos/busca-rapida?q=CF-25&deposito_id={did}", headers=h)
    assert r.status_code == 200, r.get_json()
    assert r.get_json()["produtos"][0]["id"] == pid
