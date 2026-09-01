"""Parâmetros de planejamento por produto/depósito (EST-005)."""
from __future__ import annotations

from catalog_server import auth_token, permissao
from catalog_server.app_factory import create_app
from catalog_server.db import system_conn
from catalog_server.services import estoque_parametro as param_svc


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
    uid = _usuario("paradmin")
    with system_conn() as conn:
        conn.execute(
            "INSERT INTO usuario_perfis (usuario_id, perfil_id) VALUES (%s,%s) ON CONFLICT DO NOTHING",
            (uid, _perfil_id("Administrador")),
        )
        conn.commit()
    permissao.invalidar(uid)
    return create_app().test_client(), _token(uid, "paradmin")


def _setup(system_db) -> tuple[int, int]:
    with system_conn() as conn:
        conn.execute("INSERT INTO produtos_cadastro (nome, ativo, sku, preco) VALUES (%s,%s,%s,%s)", ("Prod", 1, "P-1", 10.0))
        pid = int(conn.execute("SELECT lastval()").fetchone()["lastval"])
        did = int(conn.execute("SELECT id FROM depositos ORDER BY id LIMIT 1").fetchone()["id"])
        conn.commit()
        return pid, did


def test_salvar_listar(system_db):
    pid, did = _setup(system_db)
    p = param_svc.salvar(pid, did, "manual", 5, 50, 8, 10, 3, 10, 50, 5, None, "manual", "reposição semanal", None)
    assert float(p["minimo"]) == 5
    assert p["lead_time_dias"] == 3
    assert float(p["lote_multiplo"]) == 5
    lista = param_svc.listar(pid)
    assert len(lista) == 1
    assert lista[0]["motivo"] == "reposição semanal"


def test_upsert_versiona(system_db):
    pid, did = _setup(system_db)
    param_svc.salvar(pid, did, "manual", 5, 50, None, None, None, None, None, None, None, "manual", None, None)
    p2 = param_svc.salvar(pid, did, "calculada", 7, 60, None, None, None, None, None, None, None, "abc", "auto", None)
    assert p2["versao"] == 2
    assert p2["politica"] == "calculada"
    assert len(param_svc.listar(pid)) == 1  # apenas a ativa


def test_obter_efetivo_fallback_legado(system_db):
    pid, did = _setup(system_db)
    with system_conn() as conn:
        conn.execute(
            "INSERT INTO estoque_saldo (produto_id, deposito_id, quantidade, estoque_minimo, estoque_maximo) "
            "VALUES (%s,%s,10,%s,%s)",
            (pid, did, 3, 30),
        )
        conn.commit()
    ef = param_svc.obter_efetivo(pid, did)
    assert ef["minimo_origem"] == "legado"
    assert float(ef["minimo"]) == 3
    # após salvar parâmetro, passa a vir do parâmetro
    param_svc.salvar(pid, did, "manual", 5, 50, None, None, None, None, None, None, None, "manual", None, None)
    ef2 = param_svc.obter_efetivo(pid, did)
    assert ef2["minimo_origem"] == "parametro"
    assert float(ef2["minimo"]) == 5


def test_validacoes(system_db):
    pid, did = _setup(system_db)
    try:
        param_svc.salvar(pid, did, "x", None, None, None, None, None, None, None, None, None, "manual", None, None)
        assert False, "política inválida deveria falhar"
    except ValueError:
        pass
    try:
        param_svc.salvar(pid, did, "manual", None, None, None, None, None, None, None, None, None, "x", None, None)
        assert False, "fonte inválida deveria falhar"
    except ValueError:
        pass


def test_excluir(system_db):
    pid, did = _setup(system_db)
    param_svc.salvar(pid, did, "manual", 5, 50, None, None, None, None, None, None, None, "manual", None, None)
    assert param_svc.excluir(pid, did) is True
    assert param_svc.listar(pid) == []
    assert param_svc.excluir(pid, did) is False


def test_api_fluxo(system_db):
    client, h = _cliente_admin(system_db)
    pid, did = _setup(system_db)
    r = client.post("/api/estoque/parametros", headers=h, json={
        "produto_id": pid, "deposito_id": did, "politica": "manual",
        "minimo": 5, "maximo": 50, "ponto_pedido": 8, "estoque_seguranca": 10, "lead_time_dias": 3,
    })
    assert r.status_code == 200, r.get_json()
    r = client.get(f"/api/estoque/parametros?produto_id={pid}", headers=h)
    assert len(r.get_json()["parametros"]) == 1
    r = client.get(f"/api/estoque/parametros/efetivo?produto_id={pid}&deposito_id={did}", headers=h)
    assert r.get_json()["minimo_origem"] == "parametro"
    r = client.delete(f"/api/estoque/parametros?produto_id={pid}&deposito_id={did}", headers=h)
    assert r.status_code == 200


def test_api_parametro_invalido(system_db):
    client, h = _cliente_admin(system_db)
    pid, did = _setup(system_db)
    r = client.post("/api/estoque/parametros", headers=h, json={"produto_id": pid, "deposito_id": did, "politica": "x"})
    assert r.status_code == 400


def test_api_rbac_negado(system_db):
    uid = _usuario("parsem")
    permissao.invalidar(uid)
    client = create_app().test_client()
    h = _token(uid, "parsem")
    r = client.get("/api/estoque/parametros?produto_id=1", headers=h)
    assert r.status_code == 403