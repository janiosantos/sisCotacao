"""Regras de preço com prioridade, contexto e vigência (MDM-007)."""
from __future__ import annotations

from catalog_server import auth_token, permissao
from catalog_server.app_factory import create_app
from catalog_server.db import system_conn
from catalog_server.services import preco_regra as regra_svc
from catalog_server.services import pricing_engine


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
    uid = _usuario("precadmin")
    with system_conn() as conn:
        conn.execute(
            "INSERT INTO usuario_perfis (usuario_id, perfil_id) VALUES (%s,%s) ON CONFLICT DO NOTHING",
            (uid, _perfil_id("Administrador")),
        )
        conn.commit()
    permissao.invalidar(uid)
    return create_app().test_client(), _token(uid, "precadmin")


def _produto(system_db, sku: str = "PR-1", preco: float = 10.0, custo: float = 5.0) -> int:
    with system_conn() as conn:
        conn.execute(
            "INSERT INTO produtos_cadastro (nome, ativo, sku, ean, preco, custo_unitario) "
            "VALUES (%s,%s,%s,%s,%s,%s)",
            ("Produto", 1, sku, "7891000000007", preco, custo),
        )
        pid = int(conn.execute("SELECT lastval()").fetchone()["lastval"])
        conn.commit()
        return pid


def test_salvar_listar(system_db):
    pid = _produto(system_db)
    r = regra_svc.salvar(pid, 1, "varejo", None, None, None, 15.0, None, None, None, None, "cliente especial", None)
    assert float(r["preco"]) == 15.0
    assert r["prioridade"] == 1
    lista = regra_svc.listar(pid)
    assert len(lista) == 1
    assert lista[0]["motivo"] == "cliente especial"


def test_resolver_prioridade_e_contexto(system_db):
    pid = _produto(system_db)
    regra_svc.salvar(pid, 5, "atacado", None, None, None, 12.0, None, None, None, None, None, None)
    regra_svc.salvar(pid, 1, "varejo", None, None, None, 14.0, None, None, None, None, None, None)
    # contexto casa: canal varejo -> prioridade 1
    r = regra_svc.resolver(pid, canal="varejo")
    assert float(r["preco"]) == 14.0
    # canal atacado -> prioridade 5
    r2 = regra_svc.resolver(pid, canal="atacado")
    assert float(r2["preco"]) == 12.0
    # sem contexto (canal diferente) -> None
    assert regra_svc.resolver(pid, canal="contrato") is None


def test_resolver_cliente_segmento_quantidade(system_db):
    pid = _produto(system_db)
    regra_svc.salvar(pid, 1, None, 77, None, None, 9.0, None, None, None, None, None, None)
    regra_svc.salvar(pid, 2, None, None, "construtora", None, None, 10.0, None, None, None, None, None)
    regra_svc.salvar(pid, 3, None, None, None, 50, None, 5.0, None, None, None, None, None)
    assert float(regra_svc.resolver(pid, cliente_id=77)["preco"]) == 9.0
    assert float(regra_svc.resolver(pid, segmento="construtora")["desconto_pct"]) == 10.0
    assert float(regra_svc.resolver(pid, quantidade=60)["desconto_pct"]) == 5.0
    assert regra_svc.resolver(pid, quantidade=10) is None


def test_preco_efetivo_aplica_regra(system_db):
    pid = _produto(system_db, preco=10.0)
    regra_svc.salvar(pid, 1, "varejo", None, None, None, 15.0, None, None, None, None, "promo", None)
    resp = pricing_engine.preco_efetivo(pid, canal="varejo")
    assert resp["origem"] == "regra"
    assert resp["preco"] == 15.0
    assert "Regra" in resp["explicacao"]


def test_preco_efetivo_sem_regra_usa_tabela_base(system_db):
    pid = _produto(system_db, preco=10.0, custo=None)  # sem custo → origem base (não motor)
    resp = pricing_engine.preco_efetivo(pid, canal="varejo")
    assert resp["origem"] != "regra"
    assert resp["preco"] == 10.0


def test_margem_minima_flag(system_db):
    pid = _produto(system_db, preco=10.0, custo=9.0)  # custo quase igual ao preço
    regra_svc.salvar(pid, 1, "varejo", None, None, None, 10.0, None, 40.0, None, None, None, None)
    resp = pricing_engine.preco_efetivo(pid, canal="varejo")
    assert resp["origem"] == "regra"
    assert resp.get("abaixo_da_margem_minima") is True
    assert resp.get("margem_minima_pct") == 40.0


def test_validacoes(system_db):
    pid = _produto(system_db)
    try:
        regra_svc.salvar(pid, 1, None, None, None, None, -1, None, None, None, None, None, None)
        assert False, "preco negativo deveria falhar"
    except ValueError:
        pass
    try:
        regra_svc.salvar(pid, 1, None, None, None, None, None, None, None, None, None, None, None)
        assert False, "sem preco/desconto deveria falhar"
    except ValueError:
        pass


def test_api_fluxo(system_db):
    client, h = _cliente_admin(system_db)
    pid = _produto(system_db)
    r = client.post(f"/api/precos/regras/{pid}", headers=h, json={
        "prioridade": 1, "canal": "varejo", "preco": 15.0,
    })
    assert r.status_code == 200, r.get_json()
    rid = r.get_json()["regra"]["id"]

    r = client.get(f"/api/precos/regras/{pid}", headers=h)
    assert len(r.get_json()["regras"]) == 1

    r = client.get(f"/api/precos/efetivo/{pid}?canal=varejo", headers=h)
    body = r.get_json()
    assert body["origem"] == "regra"
    assert body["preco"] == 15.0

    r = client.delete(f"/api/precos/regras/{pid}/{rid}", headers=h)
    assert r.status_code == 200


def test_api_regra_invalida(system_db):
    client, h = _cliente_admin(system_db)
    pid = _produto(system_db)
    r = client.post(f"/api/precos/regras/{pid}", headers=h, json={"preco": -5})
    assert r.status_code == 400
    assert r.get_json()["code"] == "regra_preco_invalida"


def test_api_rbac_negado_sem_permissao(system_db):
    uid = _usuario("precsem")
    permissao.invalidar(uid)
    client = create_app().test_client()
    h = _token(uid, "precsem")
    pid = _produto(system_db)
    r = client.get(f"/api/precos/regras/{pid}", headers=h)
    assert r.status_code == 403