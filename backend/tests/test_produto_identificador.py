"""Identificadores m�ltiplos de produto (MDM-003)."""
from __future__ import annotations

from catalog_server import auth_token, permissao
from catalog_server.app_factory import create_app
from catalog_server.db import system_conn
from catalog_server.services import produto_identificador as ident_svc


def _usuario(login: str) -> int:
    from werkzeug.security import generate_password_hash

    with system_conn() as conn:
        cur = conn.execute(
            "INSERT INTO usuarios (nome, login, senha_hash) VALUES (%s,%s,%s)",
            ("Operador", login, generate_password_hash("x123")),
        )
        uid = int(cur.lastrowid)
        conn.commit()
    return uid


def _perfil_id(nome: str) -> int:
    with system_conn() as conn:
        return int(conn.execute("SELECT id FROM perfis WHERE nome=%s", (nome,)).fetchone()["id"])


def _token(usuario_id: int, login: str) -> dict:
    return {"Authorization": f"Bearer {auth_token.criar_token({'id': usuario_id, 'login': login})}"}


def _cliente_admin(system_db):
    uid = _usuario("identadmin")
    with system_conn() as conn:
        conn.execute(
            "INSERT INTO usuario_perfis (usuario_id, perfil_id) VALUES (%s,%s) ON CONFLICT DO NOTHING",
            (uid, _perfil_id("Administrador")),
        )
        conn.commit()
    permissao.invalidar(uid)
    return create_app().test_client(), _token(uid, "identadmin")


def _produto(system_db, sku: str = "CF-25", ean: str = "7891000000002") -> int:
    with system_conn() as conn:
        pid = int(conn.execute(
            "INSERT INTO produtos_cadastro (nome, ativo, sku, ean, preco) VALUES (%s,%s,%s,%s,%s) RETURNING id",
            ('Cabo Flexível 2,5mm', 1, sku, ean, 3.2),
        ).fetchone()["id"])
        conn.commit()
        return pid


def test_salvar_listar(system_db):
    pid = _produto(system_db)
    ident_svc.salvar(pid, "ean", "789 1000 0000 03", None, "manual", None)
    ident_svc.salvar(pid, "codigo_interno", "INT-001", None, "manual", None)
    lista = ident_svc.listar(pid)
    tipos = sorted(i["tipo"] for i in lista)
    assert tipos == ["codigo_interno", "ean"]
    ean = next(i for i in lista if i["tipo"] == "ean")
    assert ean["valor"] == "7891000000003"  # normalizado (dígitos)


def test_gtin_invalido(system_db):
    pid = _produto(system_db)
    try:
        ident_svc.salvar(pid, "ean", "123", None, None, None)
        assert False, "GTIN de tamanho inválido deveria falhar"
    except ValueError:
        pass


def test_duplicidade_ativa_upsert(system_db):
    pid = _produto(system_db)
    ident_svc.salvar(pid, "fornecedor", "FOR-9", None, "manual", None)
    ident_svc.salvar(pid, "fornecedor", "FOR-9", None, "manual", None)
    assert len(ident_svc.listar(pid)) == 1  # upsert, sem duplicar


def test_excluir(system_db):
    pid = _produto(system_db)
    ident = ident_svc.salvar(pid, "fabricante", "FAB-X", None, "manual", None)
    assert ident_svc.excluir(pid, ident["id"]) is True
    assert ident_svc.listar(pid) == []
    assert ident_svc.excluir(pid, ident["id"]) is False


def test_buscar_por_identificador(system_db):
    pid = _produto(system_db)
    ident_svc.salvar(pid, "codigo_interno", "INT-777", None, "manual", None)
    r = ident_svc.buscar("INT-777")
    assert any(x["id"] == pid for x in r)


def test_buscar_por_sku_legado(system_db):
    pid = _produto(system_db, sku="SKU-ABC")
    r = ident_svc.buscar("sku-abc")  # case-insensitive exato
    assert any(x["id"] == pid for x in r)


def test_buscar_por_ean_legado(system_db):
    pid = _produto(system_db, ean="7891000000002")
    r = ident_svc.buscar("7891 0000 0000 2")
    assert any(x["id"] == pid for x in r)


def test_api_fluxo(system_db):
    client, h = _cliente_admin(system_db)
    pid = _produto(system_db)
    r = client.post(f"/api/produtos-cadastro/{pid}/identificadores", headers=h, json={
        "tipo": "codigo_interno", "valor": "INT-100",
    })
    assert r.status_code == 200, r.get_json()
    iid = r.get_json()["identificador"]["id"]

    r = client.get(f"/api/produtos-cadastro/{pid}/identificadores", headers=h)
    assert len(r.get_json()["identificadores"]) == 1

    r = client.get("/api/produtos/por-codigo?q=INT-100", headers=h)
    assert any(x["id"] == pid for x in r.get_json()["produtos"])

    r = client.delete(f"/api/produtos-cadastro/{pid}/identificadores/{iid}", headers=h)
    assert r.status_code == 200
    r = client.get(f"/api/produtos-cadastro/{pid}/identificadores", headers=h)
    assert r.get_json()["identificadores"] == []


def test_api_identificador_invalido(system_db):
    client, h = _cliente_admin(system_db)
    pid = _produto(system_db)
    r = client.post(f"/api/produtos-cadastro/{pid}/identificadores", headers=h, json={
        "tipo": "ean", "valor": "123",
    })
    assert r.status_code == 400
    assert r.get_json()["code"] == "identificador_invalido"


def test_api_rbac_negado_sem_permissao(system_db):
    uid = _usuario("identsem")
    permissao.invalidar(uid)
    client = create_app().test_client()
    h = _token(uid, "identsem")
    pid = _produto(system_db)
    r = client.get(f"/api/produtos-cadastro/{pid}/identificadores", headers=h)
    assert r.status_code == 403