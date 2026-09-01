"""Inventário cíclico (EST-006): ciclo, lista, contagem, diferença e ajuste aprovado."""
from __future__ import annotations

from catalog_server import auth_token, permissao
from catalog_server.app_factory import create_app
from catalog_server.db import system_conn
from catalog_server.repositories import estoque_repo
from catalog_server.services import inventario_ciclo as inv


def _setup(system_db) -> tuple[int, int, int]:
    with system_conn() as conn:
        p1 = int(conn.execute("INSERT INTO produtos_cadastro (nome, ativo, sku, preco) VALUES (%s,%s,%s,%s) RETURNING id", ("P A", 1, "A", 10.0)).fetchone()["id"])
        p2 = int(conn.execute("INSERT INTO produtos_cadastro (nome, ativo, sku, preco) VALUES (%s,%s,%s,%s) RETURNING id", ("P B", 1, "B", 20.0)).fetchone()["id"])
        did = int(conn.execute("SELECT id FROM depositos ORDER BY id LIMIT 1").fetchone()["id"])
        conn.commit()
    estoque_repo.movimentar_fato(did, p1, "entrada", 10, custo_unitario=5.0, origem_tipo="teste")
    estoque_repo.movimentar_fato(did, p2, "entrada", 5, custo_unitario=5.0, origem_tipo="teste")
    return p1, p2, did


def test_criar_ciclo_gera_lista(system_db):
    p1, p2, did = _setup(system_db)
    c = inv.criar_ciclo(did, "Ciclo A")
    assert c["status"] == "em_andamento"
    det = inv.detalhe_ciclo(c["id"])
    assert len(det["contagens"]) == 2
    by_p = {g["produto_id"]: g for g in det["contagens"]}
    assert float(by_p[p1]["saldo_esperado"]) == 10.0
    assert float(by_p[p2]["saldo_esperado"]) == 5.0


def test_registrar_contagem_status(system_db):
    p1, _, did = _setup(system_db)
    c = inv.criar_ciclo(did, "Ciclo")
    r = inv.registrar_contagem(c["id"], p1, 12.0)
    assert r["status"] == "divergente"
    assert r["diferenca"] == 2.0
    r2 = inv.registrar_contagem(c["id"], p1, 10.0, observacao="recontado")
    assert r2["status"] == "conferido"


def test_aprovar_ajusta_saldo(system_db):
    p1, p2, did = _setup(system_db)
    c = inv.criar_ciclo(did, "Ciclo")
    inv.registrar_contagem(c["id"], p1, 12.0)
    inv.registrar_contagem(c["id"], p2, 5.0)
    res = inv.aprovar_ciclo(c["id"])
    assert res["ajustes"] == 1
    det = inv.detalhe_ciclo(c["id"])
    assert det["status"] == "ajustado"
    by_p = {g["produto_id"]: g for g in det["contagens"]}
    assert by_p[p1]["status"] == "ajustado"
    assert by_p[p2]["status"] == "ok"
    saldo = estoque_repo.saldo(deposito_id=did, produto_id=p1)[0]
    assert float(saldo["quantidade"]) == 12.0


def test_aprovar_idempotente(system_db):
    p1, p2, did = _setup(system_db)
    c = inv.criar_ciclo(did, "Ciclo")
    inv.registrar_contagem(c["id"], p1, 12.0)
    inv.registrar_contagem(c["id"], p2, 5.0)
    inv.aprovar_ciclo(c["id"])
    res2 = inv.aprovar_ciclo(c["id"])
    assert res2["duplicado"] is True
    assert res2["ajustes"] == 0
    saldo = estoque_repo.saldo(deposito_id=did, produto_id=p1)[0]
    assert float(saldo["quantidade"]) == 12.0


def test_aprovar_com_pendente_bloqueia(system_db):
    p1, p2, did = _setup(system_db)
    c = inv.criar_ciclo(did, "Ciclo")
    inv.registrar_contagem(c["id"], p1, 12.0)  # p2 fica pendente
    try:
        inv.aprovar_ciclo(c["id"])
        assert False, "aprovação com pendência deveria falhar"
    except ValueError as exc:
        assert "pendente" in str(exc)


def test_cancelar(system_db):
    _, _, did = _setup(system_db)
    c = inv.criar_ciclo(did, "Ciclo")
    assert inv.cancelar_ciclo(c["id"]) is True
    assert inv.detalhe_ciclo(c["id"])["status"] == "cancelado"
    assert inv.cancelar_ciclo(c["id"]) is False


def test_api_ciclo_fluxo(system_db):
    p1, p2, did = _setup(system_db)
    uid = _novo_usuario("cicl")
    with system_conn() as conn:
        conn.execute(
            "INSERT INTO usuario_perfis (usuario_id, perfil_id) SELECT %s, id FROM perfis WHERE nome='Administrador'",
            (uid,),
        )
        conn.commit()
    permissao.invalidar(uid)
    client = create_app().test_client()
    h = {"Authorization": f"Bearer {auth_token.criar_token({'id': uid, 'login': 'cicl'})}"}
    r = client.post("/api/estoque/inventario/ciclos", headers=h, json={"deposito_id": did, "nome": "Ciclo API"})
    assert r.status_code == 200, r.get_json()
    ciclo_id = r.get_json()["ciclo"]["id"]
    assert client.get(f"/api/estoque/inventario/ciclos/{ciclo_id}", headers=h).status_code == 200
    r = client.post(f"/api/estoque/inventario/ciclos/{ciclo_id}/contagens", headers=h,
                    json={"produto_id": p1, "quantidade_contada": 11})
    assert r.status_code == 200
    assert r.get_json()["contagem"]["status"] == "divergente"
    client.post(f"/api/estoque/inventario/ciclos/{ciclo_id}/contagens", headers=h,
                json={"produto_id": p2, "quantidade_contada": 5})
    r = client.post(f"/api/estoque/inventario/ciclos/{ciclo_id}/aprovar", headers=h)
    assert r.status_code == 200
    assert r.get_json()["resultado"]["ajustes"] == 1


def _novo_usuario(login: str) -> int:
    from werkzeug.security import generate_password_hash

    with system_conn() as conn:
        cur = conn.execute(
            "INSERT INTO usuarios (nome, login, senha_hash) VALUES (%s,%s,%s)",
            ("Op", login, generate_password_hash("x")),
        )
        uid = int(cur.lastrowid)
        conn.commit()
    return uid