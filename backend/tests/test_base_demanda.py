"""Base de demanda (COM-003): consolidação idempotente, auditável, atendida/perdida."""
from __future__ import annotations

from catalog_server import auth_token, permissao
from catalog_server.app_factory import create_app
from catalog_server.db import system_conn
from catalog_server.services import demanda as demanda_svc


def _setup(system_db) -> tuple[int, int]:
    with system_conn() as conn:
        conn.execute("INSERT INTO produtos_cadastro (nome, ativo, sku, preco) VALUES (%s,%s,%s,%s)", ("P", 1, "D-1", 10.0))
        pid = int(conn.execute("SELECT lastval()").fetchone()["lastval"])
        cid = int(conn.execute("INSERT INTO clientes (nome, doc, tipo_pessoa) VALUES (%s,%s,%s) RETURNING id", ("C", "1", "F")).fetchone()["id"])
        conn.commit()
        return pid, cid


def test_consolidar_idempotente(system_db):
    pid, cid = _setup(system_db)
    with system_conn() as conn:
        oid = int(conn.execute(
            "INSERT INTO orcamentos (cliente_id, numero, status, criado_em) VALUES (%s,%s,%s,%s) RETURNING id",
            (cid, "O-1", "finalizado", "2026-08-10 10:00:00"),
        ).fetchone()["id"])
        conn.execute(
            "INSERT INTO orcamento_itens (orcamento_id, produto_id, nome, quantidade, preco_unitario, subtotal)"
            " VALUES (%s,%s,%s,%s,%s,%s)", (oid, pid, "P", 3, 10.0, 30.0),
        )
        conn.commit()
    r1 = demanda_svc.consolidar()
    assert r1["inseridas"] == 1
    r2 = demanda_svc.consolidar()
    assert r2["inseridas"] == 0  # idempotente
    assert len(demanda_svc.listar(produto_id=pid)) == 1


def test_cancelado_nao_entra(system_db):
    pid, cid = _setup(system_db)
    with system_conn() as conn:
        oid = int(conn.execute(
            "INSERT INTO orcamentos (cliente_id, numero, status, criado_em) VALUES (%s,%s,%s,%s) RETURNING id",
            (cid, "O-2", "cancelado", "2026-08-11 10:00:00"),
        ).fetchone()["id"])
        conn.execute(
            "INSERT INTO orcamento_itens (orcamento_id, produto_id, nome, quantidade, preco_unitario, subtotal)"
            " VALUES (%s,%s,%s,%s,%s,%s)", (oid, pid, "P", 99, 10.0, 990.0),
        )
        conn.commit()
    demanda_svc.consolidar()
    assert len(demanda_svc.listar(produto_id=pid)) == 0


def test_registro_manual_e_perdida(system_db):
    pid, _ = _setup(system_db)
    r = demanda_svc.registrar_manual(pid, "2026-08-20", 5, "consumo interno", chave_manual="m1")
    assert demanda_svc.marcar_perdida(r["id"], "ruptura na prateleira") is True
    aud = demanda_svc.auditar(pid)
    assert float(aud["resumo"]["perdida"]) == 5.0
    assert aud["itens"][0]["status"] == "perdida"
    assert aud["itens"][0]["motivo_ruptura"] == "ruptura na prateleira"


def test_registro_manual_idempotente(system_db):
    pid, _ = _setup(system_db)
    demanda_svc.registrar_manual(pid, "2026-08-20", 5, chave_manual="m2")
    try:
        demanda_svc.registrar_manual(pid, "2026-08-20", 5, chave_manual="m2")
        assert False, "chave manual repetida deveria falhar (UNIQUE)"
    except Exception:
        pass


def test_auditoria_documento(system_db):
    pid, cid = _setup(system_db)
    with system_conn() as conn:
        oid = int(conn.execute(
            "INSERT INTO orcamentos (cliente_id, numero, status, criado_em) VALUES (%s,%s,%s,%s) RETURNING id",
            (cid, "O-3", "finalizado", "2026-08-15 10:00:00"),
        ).fetchone()["id"])
        conn.execute(
            "INSERT INTO orcamento_itens (orcamento_id, produto_id, nome, quantidade, preco_unitario, subtotal)"
            " VALUES (%s,%s,%s,%s,%s,%s)", (oid, pid, "P", 2, 10.0, 20.0),
        )
        conn.commit()
    demanda_svc.consolidar()
    aud = demanda_svc.auditar(pid)
    assert aud["itens"][0]["documento"] == "O-3"


def test_api_demanda_fluxo(system_db):
    pid, _ = _setup(system_db)
    uid = _usuario("demr")
    with system_conn() as conn:
        conn.execute(
            "INSERT INTO usuario_perfis (usuario_id, perfil_id) SELECT %s, id FROM perfis WHERE nome='Administrador'",
            (uid,),
        )
        conn.commit()
    permissao.invalidar(uid)
    client = create_app().test_client()
    h = {"Authorization": f"Bearer {auth_token.criar_token({'id': uid, 'login': 'demr'})}"}
    r = client.post("/api/estoque/demanda/consolidar", headers=h, json={})
    assert r.status_code == 200
    r = client.post("/api/estoque/demanda", headers=h, json={"produto_id": pid, "data": "2026-08-25", "quantidade": 7, "chave_manual": "api-1"})
    assert r.status_code == 200, r.get_json()
    dem_id = r.get_json()["demanda"]["id"]
    assert client.get(f"/api/estoque/demanda?produto_id={pid}", headers=h).status_code == 200
    assert client.get(f"/api/estoque/demanda/auditar/{pid}", headers=h).status_code == 200
    r = client.post(f"/api/estoque/demanda/{dem_id}/perdida", headers=h, json={"motivo": "estoque zerado"})
    assert r.status_code == 200


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