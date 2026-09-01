"""Valorização de estoque por custo médio e data de corte (EST-004)."""
from __future__ import annotations

from catalog_server import auth_token, permissao
from catalog_server.app_factory import create_app
from catalog_server.db import system_conn
from catalog_server.repositories import estoque_repo


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
    uid = _usuario("valadmin")
    with system_conn() as conn:
        conn.execute(
            "INSERT INTO usuario_perfis (usuario_id, perfil_id) VALUES (%s,%s) ON CONFLICT DO NOTHING",
            (uid, _perfil_id("Administrador")),
        )
        conn.commit()
    permissao.invalidar(uid)
    return create_app().test_client(), _token(uid, "valadmin")


def _setup(system_db) -> tuple[int, int]:
    with system_conn() as conn:
        conn.execute("INSERT INTO produtos_cadastro (nome, ativo, sku, preco) VALUES (%s,%s,%s,%s)", ("Prod A", 1, "A-1", 10.0))
        pid = int(conn.execute("SELECT lastval()").fetchone()["lastval"])
        did = int(conn.execute("SELECT id FROM depositos ORDER BY id LIMIT 1").fetchone()["id"])
        conn.commit()
        return pid, did


def test_valorizacao_vigente(system_db):
    pid, did = _setup(system_db)
    estoque_repo.movimentar_fato(did, pid, "entrada", 10, custo_unitario=5.0, origem_tipo="teste")
    estoque_repo.movimentar_fato(did, pid, "entrada", 10, custo_unitario=7.0, origem_tipo="teste")
    v = estoque_repo.valorizar(did)
    assert v["total"] == 120.0  # 20 un × 6,00
    item = v["itens"][0]
    assert float(item["custo_medio"]) == 6.0
    assert float(item["quantidade"]) == 20.0


def test_valorizacao_por_produto(system_db):
    pid, did = _setup(system_db)
    estoque_repo.movimentar_fato(did, pid, "entrada", 10, custo_unitario=5.0, origem_tipo="teste")
    v = estoque_repo.valorizar(did, produto_id=pid)
    assert v["total"] == 50.0
    assert len(v["itens"]) == 1


def test_valorizacao_data_corte(system_db):
    pid, did = _setup(system_db)
    # primeiro fato (custo 5) com criado_em forçado em data antiga
    with system_conn() as conn:
        m1 = estoque_repo.movimentar_fato(did, pid, "entrada", 10, custo_unitario=5.0, origem_tipo="teste")
        conn.execute(
            "UPDATE estoque_movimento SET criado_em='2026-01-01 10:00:00' WHERE id=?",
            (m1["movimento_id"],),
        )
        conn.commit()
    # segundo fato (custo 7) recente
    estoque_repo.movimentar_fato(did, pid, "entrada", 10, custo_unitario=7.0, origem_tipo="teste")
    # vigente: 20 un × 6 = 120
    v_agora = estoque_repo.valorizar(did)
    assert v_agora["total"] == 120.0
    # corte em 2026-01-01: apenas o 1º fato (10 un × 5 = 50)
    v_corte = estoque_repo.valorizar(did, data_corte="2026-01-01")
    assert v_corte["total"] == 50.0
    assert float(v_corte["itens"][0]["custo_medio"]) == 5.0
    assert float(v_corte["itens"][0]["quantidade"]) == 10.0


def test_valorizacao_sem_movimento_zero(system_db):
    pid, did = _setup(system_db)
    v = estoque_repo.valorizar(did, produto_id=pid)
    assert v["total"] == 0.0
    assert v["itens"] == []


def test_api_valorizacao(system_db):
    client, h = _cliente_admin(system_db)
    pid, did = _setup(system_db)
    estoque_repo.movimentar_fato(did, pid, "entrada", 10, custo_unitario=5.0, origem_tipo="teste")
    r = client.get(f"/api/estoque/valorizacao?deposito_id={did}", headers=h)
    assert r.status_code == 200
    assert r.get_json()["total"] == 50.0


def test_api_valorizacao_sem_deposito(system_db):
    client, h = _cliente_admin(system_db)
    r = client.get("/api/estoque/valorizacao", headers=h)
    assert r.status_code == 400


def test_api_rbac_negado(system_db):
    uid = _usuario("valsem")
    permissao.invalidar(uid)
    client = create_app().test_client()
    h = _token(uid, "valsem")
    r = client.get("/api/estoque/valorizacao?deposito_id=1", headers=h)
    assert r.status_code == 403