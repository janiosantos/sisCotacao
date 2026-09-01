"""Disponibilidade de estoque: físico, reservado, bloqueado, separação e trânsito (EST-001)."""
from __future__ import annotations

from catalog_server import auth_token, permissao
from catalog_server.app_factory import create_app
from catalog_server.db import system_conn
from catalog_server.repositories import loja


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
    uid = _usuario("estadmin")
    with system_conn() as conn:
        conn.execute(
            "INSERT INTO usuario_perfis (usuario_id, perfil_id) VALUES (%s,%s) ON CONFLICT DO NOTHING",
            (uid, _perfil_id("Administrador")),
        )
        conn.commit()
    permissao.invalidar(uid)
    return create_app().test_client(), _token(uid, "estadmin")


def _setup(system_db) -> tuple[int, int]:
    with system_conn() as conn:
        conn.execute("INSERT INTO produtos_cadastro (nome, ativo, sku, preco) VALUES (%s,%s,%s,%s)", ("Cabo", 1, "CAB-1", 5.0))
        pid = int(conn.execute("SELECT lastval()").fetchone()["lastval"])
        did = int(conn.execute("SELECT id FROM depositos ORDER BY id LIMIT 1").fetchone()["id"])
        conn.execute(
            "INSERT INTO estoque_saldo (produto_id, deposito_id, quantidade, reserva, bloqueado, separacao, transito) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s)",
            (pid, did, 10, 3, 2, 1, 5),
        )
        conn.commit()
        return pid, did


def test_disponibilidade_formula(system_db):
    pid, did = _setup(system_db)
    dep = loja.disponibilidade(pid, did)[0]
    assert float(dep["fisico"]) == 10
    assert float(dep["reservado"]) == 3
    assert float(dep["bloqueado"]) == 2
    assert float(dep["separacao"]) == 1
    assert float(dep["transito"]) == 5
    assert float(dep["disponivel"]) == 4  # 10 - 3 - 2 - 1


def test_saldo_disponivel_formula(system_db):
    pid, did = _setup(system_db)
    assert loja.saldo_disponivel(pid, did) == 4.0


def test_saldo_variante_inclui_balanços(system_db):
    pid, did = _setup(system_db)
    rows = loja.saldo_variante(pid)
    assert len(rows) == 1
    assert float(rows[0]["fisico"]) == 10
    assert float(rows[0]["reservado"]) == 3
    assert float(rows[0]["disponivel"]) == 4


def test_reserva_reduz_disponivel_nao_fisico(system_db):
    pid, did = _setup(system_db)
    with system_conn() as conn:
        conn.execute("UPDATE estoque_saldo SET reserva=5 WHERE produto_id=%s AND deposito_id=%s", (pid, did))
        conn.commit()
    dep = loja.disponibilidade(pid, did)[0]
    assert float(dep["fisico"]) == 10  # físico não muda
    assert float(dep["disponivel"]) == 2  # 10 - 5 - 2 - 1


def test_colunas_existem(system_db):
    with system_conn() as conn:
        cols = {r["column_name"] for r in conn.execute(
            "SELECT column_name FROM information_schema.columns WHERE table_name='estoque_saldo'"
        ).fetchall()}
    for col in ("bloqueado", "separacao", "transito"):
        assert col in cols


def test_api_disponibilidade(system_db):
    client, h = _cliente_admin(system_db)
    pid, did = _setup(system_db)
    r = client.get(f"/api/estoque/disponibilidade/{pid}", headers=h)
    assert r.status_code == 200
    body = r.get_json()
    assert body["produto_id"] == pid
    dep = body["depositos"][0]
    assert float(dep["disponivel"]) == 4


def test_api_rbac_negado_sem_permissao(system_db):
    uid = _usuario("estsem")
    permissao.invalidar(uid)
    client = create_app().test_client()
    h = _token(uid, "estsem")
    pid, _ = _setup(system_db)
    r = client.get(f"/api/estoque/disponibilidade/{pid}", headers=h)
    assert r.status_code == 403