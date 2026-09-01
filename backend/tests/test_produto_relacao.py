"""Relações entre produtos: equivalentes, substitutos, acessórios e kits (MDM-005)."""
from __future__ import annotations

from catalog_server import auth_token, permissao
from catalog_server.app_factory import create_app
from catalog_server.db import system_conn
from catalog_server.services import produto_relacao as rel_svc


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
    uid = _usuario("reladmin")
    with system_conn() as conn:
        conn.execute(
            "INSERT INTO usuario_perfis (usuario_id, perfil_id) VALUES (%s,%s) ON CONFLICT DO NOTHING",
            (uid, _perfil_id("Administrador")),
        )
        conn.commit()
    permissao.invalidar(uid)
    return create_app().test_client(), _token(uid, "reladmin")


def _produto(system_db, nome: str, sku: str) -> int:
    with system_conn() as conn:
        pid = int(conn.execute(
            "INSERT INTO produtos_cadastro (nome, ativo, sku, preco) VALUES (%s,%s,%s,%s) RETURNING id",
            (nome, 1, sku, 1.0),
        ).fetchone()["id"])
        conn.commit()
        return pid


def test_salvar_listar(system_db):
    a = _produto(system_db, "Chave 12", "CH-12")
    b = _produto(system_db, "Chave 13", "CH-13")
    rel_svc.salvar(a, b, "substituto", 1, 2, None, None, "tamanho acima", None)
    rel_svc.salvar(a, b, "acessorio", 1, 1, None, None, None, None)
    lista = rel_svc.listar(a)
    assert len(lista) == 2
    subst = [r for r in lista if r["tipo"] == "substituto"][0]
    assert subst["relacionado_id"] == b
    assert subst["prioridade"] == 2
    assert subst["motivo"] == "tamanho acima"


def test_upsert_e_versionamento(system_db):
    a = _produto(system_db, "A", "A-1")
    b = _produto(system_db, "B", "B-1")
    rel_svc.salvar(a, b, "equivalente", 1, 1, None, None, None, None)
    r2 = rel_svc.salvar(a, b, "equivalente", 2, 1, None, None, "novo", None)
    assert r2["versao"] == 2
    assert len(rel_svc.listar(a)) == 1  # apenas a ativa
    assert rel_svc.listar(a)[0]["fator"] == 2


def test_relacionados_dupla_direcao(system_db):
    a = _produto(system_db, "A", "A-1")
    b = _produto(system_db, "B", "B-1")
    c = _produto(system_db, "C", "C-1")
    rel_svc.salvar(a, b, "substituto", 1, 1, None, None, None, None)
    rel_svc.salvar(c, a, "complementar", 1, 1, None, None, None, None)
    rels = rel_svc.relacionados(a)
    outros = sorted(r["outro_sku"] for r in rels)
    assert outros == ["B-1", "C-1"]


def test_kit_componentes(system_db):
    kit = _produto(system_db, "Kit Parafusos", "KIT-1")
    p1 = _produto(system_db, "Parafuso 10", "PAR-10")
    p2 = _produto(system_db, "Arruela 10", "ARR-10")
    rel_svc.salvar(kit, p1, "componente", 4, 1, None, None, None, None)
    rel_svc.salvar(kit, p2, "componente", 4, 2, None, None, None, None)
    comps = rel_svc.listar(kit, "componente")
    assert len(comps) == 2
    assert all(c["tipo"] == "componente" for c in comps)


def test_validacoes(system_db):
    a = _produto(system_db, "A", "A-1")
    try:
        rel_svc.salvar(a, a, "equivalente", 1, 1, None, None, None, None)
        assert False, "produto==relacionado deveria falhar"
    except ValueError:
        pass
    try:
        rel_svc.salvar(a, _produto(system_db, "B", "B-1"), "nao_existe", 1, 1, None, None, None, None)
        assert False, "tipo inválido deveria falhar"
    except ValueError:
        pass


def test_excluir(system_db):
    a = _produto(system_db, "A", "A-1")
    b = _produto(system_db, "B", "B-1")
    rel = rel_svc.salvar(a, b, "equivalente", 1, 1, None, None, None, None)
    assert rel_svc.excluir(a, rel["id"]) is True
    assert rel_svc.listar(a) == []
    assert rel_svc.excluir(a, rel["id"]) is False


def test_api_fluxo(system_db):
    client, h = _cliente_admin(system_db)
    a = _produto(system_db, "A", "A-1")
    b = _produto(system_db, "B", "B-1")

    r = client.post(f"/api/produtos-cadastro/{a}/relacoes", headers=h, json={
        "relacionado_id": b, "tipo": "substituto", "fator": 1, "prioridade": 1,
    })
    assert r.status_code == 200, r.get_json()
    rid = r.get_json()["relacao"]["id"]

    r = client.get(f"/api/produtos-cadastro/{a}/relacoes", headers=h)
    assert len(r.get_json()["relacoes"]) == 1

    r = client.get(f"/api/produtos-cadastro/{a}/relacoes/relacionados", headers=h)
    assert any(x["outro_id"] == b for x in r.get_json()["relacionados"])

    r = client.delete(f"/api/produtos-cadastro/{a}/relacoes/{rid}", headers=h)
    assert r.status_code == 200


def test_api_relacao_invalida(system_db):
    client, h = _cliente_admin(system_db)
    a = _produto(system_db, "A", "A-1")
    b = _produto(system_db, "B", "B-1")
    r = client.post(f"/api/produtos-cadastro/{a}/relacoes", headers=h, json={
        "relacionado_id": b, "tipo": "x", "fator": 1,
    })
    assert r.status_code == 400
    assert r.get_json()["code"] == "relacao_invalida"


def test_api_rbac_negado_sem_permissao(system_db):
    uid = _usuario("relsem")
    permissao.invalidar(uid)
    client = create_app().test_client()
    h = _token(uid, "relsem")
    a = _produto(system_db, "A", "A-1")
    r = client.get(f"/api/produtos-cadastro/{a}/relacoes", headers=h)
    assert r.status_code == 403