"""Endereçamento (EST-007): posições, saldo por posição, posição primária e movimentação logada."""
from __future__ import annotations

from catalog_server import auth_token, permissao
from catalog_server.app_factory import create_app
from catalog_server.db import system_conn
from catalog_server.services import endereco as end_svc


def _setup(system_db) -> tuple[int, int]:
    with system_conn() as conn:
        pid = int(conn.execute("INSERT INTO produtos_cadastro (nome, ativo, sku, preco) VALUES (%s,%s,%s,%s) RETURNING id", ("P", 1, "E-1", 10.0)).fetchone()["id"])
        did = int(conn.execute("SELECT id FROM depositos ORDER BY id LIMIT 1").fetchone()["id"])
        conn.commit()
        return pid, did


def test_criar_listar_excluir_posicao(system_db):
    _, did = _setup(system_db)
    p = end_svc.criar_posicao(did, "A-01-02-1")
    assert p["codigo"] == "A-01-02-1"
    assert len(end_svc.listar_posicoes(did)) == 1
    assert end_svc.excluir_posicao(p["id"]) is True
    assert end_svc.listar_posicoes(did) == []


def test_codigo_duplicado_rejeita(system_db):
    _, did = _setup(system_db)
    end_svc.criar_posicao(did, "A-01-02-1")
    try:
        end_svc.criar_posicao(did, "a-01-02-1")
        assert False, "código duplicado deveria falhar"
    except ValueError:
        pass


def test_entrada_saida_e_primaria(system_db):
    pid, did = _setup(system_db)
    p1 = end_svc.criar_posicao(did, "A-01")
    p2 = end_svc.criar_posicao(did, "A-02")
    end_svc.movimentar(None, p1["id"], pid, 10)
    est = end_svc.estoque_na_posicao(p1["id"])
    assert len(est) == 1 and float(est[0]["quantidade"]) == 10.0
    assert end_svc.posicao_primaria(pid, did)["posicao_id"] == p1["id"]
    end_svc.movimentar(None, p2["id"], pid, 5)
    # primária continua a primeira (p1)
    assert end_svc.posicao_primaria(pid, did)["posicao_id"] == p1["id"]


def test_movimentar_entre_posicoes(system_db):
    pid, did = _setup(system_db)
    p1 = end_svc.criar_posicao(did, "A-01")
    p2 = end_svc.criar_posicao(did, "A-02")
    end_svc.movimentar(None, p1["id"], pid, 10)
    end_svc.movimentar(p1["id"], p2["id"], pid, 4)
    assert float(end_svc.estoque_na_posicao(p1["id"])[0]["quantidade"]) == 6.0
    assert float(end_svc.estoque_na_posicao(p2["id"])[0]["quantidade"]) == 4.0
    movs = end_svc.ultimos_movimentos()
    # 1 entrada + 2 movimentações (origem e destino)
    assert len(movs) == 3


def test_movimentar_sem_estoque_rejeita(system_db):
    pid, did = _setup(system_db)
    p1 = end_svc.criar_posicao(did, "A-01")
    p2 = end_svc.criar_posicao(did, "A-02")
    try:
        end_svc.movimentar(p1["id"], p2["id"], pid, 5)
        assert False, "mover sem estoque deveria falhar"
    except ValueError as exc:
        assert "insuficiente" in str(exc)


def test_excluir_posicao_ocupada_rejeita(system_db):
    pid, did = _setup(system_db)
    p1 = end_svc.criar_posicao(did, "A-01")
    end_svc.movimentar(None, p1["id"], pid, 3)
    try:
        end_svc.excluir_posicao(p1["id"])
        assert False, "excluir posição ocupada deveria falhar"
    except ValueError:
        pass


def test_api_fluxo(system_db):
    pid, did = _setup(system_db)
    uid = _usuario("endr")
    with system_conn() as conn:
        conn.execute(
            "INSERT INTO usuario_perfis (usuario_id, perfil_id) SELECT %s, id FROM perfis WHERE nome='Administrador'",
            (uid,),
        )
        conn.commit()
    permissao.invalidar(uid)
    client = create_app().test_client()
    h = {"Authorization": f"Bearer {auth_token.criar_token({'id': uid, 'login': 'endr'})}"}
    r = client.post("/api/estoque/enderecos", headers=h, json={"deposito_id": did, "codigo": "B-01"})
    assert r.status_code == 200
    pos_id = r.get_json()["posicao"]["id"]
    assert client.get("/api/estoque/enderecos?deposito_id=" + str(did), headers=h).status_code == 200
    r = client.post("/api/estoque/enderecos/movimentar", headers=h,
                    json={"produto_id": pid, "quantidade": 7, "para_posicao_id": pos_id})
    assert r.status_code == 200
    r = client.get(f"/api/estoque/enderecos/{pos_id}/estoque", headers=h)
    assert float(r.get_json()["itens"][0]["quantidade"]) == 7.0
    assert client.get(f"/api/estoque/enderecos/primaria/{pid}?deposito_id={did}", headers=h).status_code == 200
    assert client.get("/api/estoque/enderecos/movimentos", headers=h).status_code == 200


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