"""Conversões de unidade por produto/embalagem (MDM-002)."""
from __future__ import annotations

from catalog_server import auth_token, permissao
from catalog_server.app_factory import create_app
from catalog_server.db import system_conn
from catalog_server.services import unidade_conversao as conv_svc


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
    uid = _usuario("convadmin")
    with system_conn() as conn:
        conn.execute(
            "INSERT INTO usuario_perfis (usuario_id, perfil_id) VALUES (%s,%s) ON CONFLICT DO NOTHING",
            (uid, _perfil_id("Administrador")),
        )
        conn.commit()
    permissao.invalidar(uid)
    return create_app().test_client(), _token(uid, "convadmin")


def _produto(system_db) -> int:
    with system_conn() as conn:
        conn.execute(
            "INSERT INTO produtos_cadastro (nome, ativo, sku, ean, preco, unidade_venda, fator_conversao)"
            " VALUES (%s,%s,%s,%s,%s,%s,%s)",
            ('Cabo Flexível 2,5mm', 1, 'CF-25', '7891000000002', 3.2, 'RL', 100),
        )
        pid = int(conn.execute("SELECT lastval()").fetchone()["lastval"])
        conn.commit()
        return pid


def test_salvar_listar_conversao(system_db):
    pid = _produto(system_db)
    c = conv_svc.salvar(pid, "CX", "UN", 12, "UN", None)
    assert c["unidade_origem"] == "CX"
    assert c["unidade_destino"] == "UN"
    assert float(c["fator"]) == 12
    assert c["unidade_base"] == "UN"
    assert c["versao"] == 1

    lista = conv_svc.listar(pid)
    assert len(lista) == 1
    assert lista[0]["unidade_origem"] == "CX"


def test_atualizacao_versiona_e_nao_duplica(system_db):
    pid = _produto(system_db)
    conv_svc.salvar(pid, "CX", "UN", 12, "UN", None)
    c2 = conv_svc.salvar(pid, "CX", "UN", 24, "UN", None)
    assert c2["versao"] == 2
    lista = conv_svc.listar(pid)
    assert len(lista) == 1  # apenas a ativa
    assert float(lista[0]["fator"]) == 24
    with system_conn() as conn:
        total = int(conn.execute(
            "SELECT COUNT(*) AS n FROM unidade_conversao WHERE produto_id=%s", (pid,)
        ).fetchone()["n"])
    assert total == 2  # histórico preservado


def test_excluir_conversao(system_db):
    pid = _produto(system_db)
    conv_svc.salvar(pid, "CX", "UN", 12, "UN", None)
    assert conv_svc.excluir(pid, "CX", None) is True
    assert conv_svc.listar(pid) == []
    assert conv_svc.excluir(pid, "CX", None) is False


def test_converter_direto(system_db):
    pid = _produto(system_db)
    conv_svc.salvar(pid, "CX", "UN", 12, "UN", None)
    r = conv_svc.converter(pid, 2, "CX", "UN")
    assert float(r["resultado"]) == 24
    assert r["unidade_base"] == "UN"
    # inverso: 24 UN -> 2 CX
    r2 = conv_svc.converter(pid, 24, "UN", "CX")
    assert float(r2["resultado"]) == 2


def test_converter_cadeia(system_db):
    pid = _produto(system_db)
    conv_svc.salvar(pid, "CX", "UN", 12, "UN", None)
    conv_svc.salvar(pid, "PCT", "UN", 3, "UN", None)
    # 2 PCT = 6 UN; 1 CX = 12 UN -> 2 PCT em CX = 0,5 CX
    r = conv_svc.converter(pid, 2, "PCT", "CX")
    assert float(r["resultado"]) == 0.5


def test_converter_sem_conversao_fallback(system_db):
    pid = _produto(system_db)  # produto tem unidade_venda=RL, sem conversão configurada
    r = conv_svc.converter(pid, 5, "RL", "RL")
    assert float(r["resultado"]) == 5
    assert float(r["fator"]) == 1


def test_validacoes(system_db):
    pid = _produto(system_db)
    try:
        conv_svc.salvar(pid, "CX", "UN", 0, "UN", None)
        assert False, "fator<=0 deveria falhar"
    except ValueError:
        pass
    try:
        conv_svc.salvar(pid, "CX", "CX", 1, "UN", None)
        assert False, "origem==destino deveria falhar"
    except ValueError:
        pass


def test_api_conversoes_fluxo(system_db):
    client, h = _cliente_admin(system_db)
    pid = _produto(system_db)

    r = client.post(f"/api/produtos-cadastro/{pid}/conversoes", headers=h, json={
        "unidade_origem": "CX", "unidade_destino": "UN", "fator": 12, "unidade_base": "UN",
    })
    assert r.status_code == 200, r.get_json()

    r = client.get(f"/api/produtos-cadastro/{pid}/conversoes", headers=h)
    body = r.get_json()
    assert len(body["conversoes"]) == 1
    assert body["conversoes"][0]["unidade_origem"] == "CX"

    r = client.get(f"/api/produtos-cadastro/{pid}/conversao?qtd=2&de=CX&para=UN", headers=h)
    assert float(r.get_json()["resultado"]) == 24

    r = client.delete(f"/api/produtos-cadastro/{pid}/conversoes/CX", headers=h)
    assert r.status_code == 200
    r = client.get(f"/api/produtos-cadastro/{pid}/conversoes", headers=h)
    assert r.get_json()["conversoes"] == []


def test_api_conversao_invalida(system_db):
    client, h = _cliente_admin(system_db)
    pid = _produto(system_db)
    r = client.post(f"/api/produtos-cadastro/{pid}/conversoes", headers=h, json={
        "unidade_origem": "CX", "unidade_destino": "UN", "fator": 0, "unidade_base": "UN",
    })
    assert r.status_code == 400
    assert r.get_json()["code"] == "conversao_invalida"


def test_api_rbac_negado_sem_permissao(system_db):
    uid = _usuario("convsem")
    permissao.invalidar(uid)  # sem perfil -> deny-by-default
    client = create_app().test_client()
    h = _token(uid, "convsem")
    pid = _produto(system_db)
    r = client.get(f"/api/produtos-cadastro/{pid}/conversoes", headers=h)
    assert r.status_code == 403