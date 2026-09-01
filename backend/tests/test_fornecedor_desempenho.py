"""Desempenho do fornecedor (COM-005): lead time real, fill rate, atraso, override manual."""
from __future__ import annotations

from catalog_server import auth_token, permissao
from catalog_server.app_factory import create_app
from catalog_server.db import system_conn
from catalog_server.services import fornecedor_desempenho as fd


def _setup(system_db) -> int:
    with system_conn() as conn:
        conn.execute("INSERT INTO fornecedores (nome, whatsapp, prazo_entrega_dias) VALUES (%s,%s,%s)", ("Fornecedor", "55", 10))
        fid = int(conn.execute("SELECT lastval()").fetchone()["lastval"])
        # 6 pedidos recebidos com lead time real
        for i in range(1, 7):
            conn.execute("INSERT INTO cotacoes (numero, status) VALUES (%s, %s)", (f"COT-{i}", "fechada"))
            cid_cot = int(conn.execute("SELECT lastval()").fetchone()["lastval"])
            conn.execute(
                "INSERT INTO pedidos_compra (numero, cotacao_id, fornecedor_id, status, data_geracao, data_prometida, data_recebida)"
                " VALUES (%s,%s,%s,%s,%s,%s,%s)",
                (f"PC-{i}", cid_cot, fid, "recebido", f"2026-08-{i:02d} 10:00:00",
                 f"2026-08-{i+5:02d} 10:00:00", f"2026-08-{i+5:02d} 12:00:00"),
            )
        conn.commit()
        return fid


def test_calcular_lead_time_fill_rate(system_db):
    fid = _setup(system_db)
    r = fd.calcular(fid)
    assert r["n_pedidos"] == 6
    assert r["lead_time_medio"] == 5.0  # 5 dias em todos
    assert r["fill_rate"] == 1.0
    assert r["confianca"] == "alta"  # >= 5 amostras
    assert r["lead_time_efetivo"] == 5.0


def test_override_manual(system_db):
    fid = _setup(system_db)
    assert fd.set_override(fid, 3, "novo fornecedor mais rápido") is True
    r = fd.calcular(fid)
    assert r["lead_time_override"] == 3
    assert r["lead_time_efetivo"] == 3  # override vence


def test_historico(system_db):
    fid = _setup(system_db)
    fd.calcular(fid)
    fd.calcular(fid)
    h = fd.historico(fid)
    assert len(h) >= 2


def test_fornecedor_inexistente(system_db):
    try:
        fd.calcular(999999)
        assert False, "fornecedor inexistente deveria falhar"
    except LookupError:
        pass


def test_api_desempenho(system_db):
    fid = _setup(system_db)
    uid = _usuario("fdes")
    with system_conn() as conn:
        conn.execute(
            "INSERT INTO usuario_perfis (usuario_id, perfil_id) SELECT %s, id FROM perfis WHERE nome='Administrador'",
            (uid,),
        )
        conn.commit()
    permissao.invalidar(uid)
    client = create_app().test_client()
    h = {"Authorization": f"Bearer {auth_token.criar_token({'id': uid, 'login': 'fdes'})}"}
    r = client.get(f"/api/estoque/fornecedores/{fid}/desempenho", headers=h)
    assert r.status_code == 200, r.get_json()
    assert r.get_json()["lead_time_medio"] == 5.0
    assert client.get(f"/api/estoque/fornecedores/{fid}/desempenho/historico", headers=h).status_code == 200
    r = client.put(f"/api/estoque/fornecedores/{fid}/lead-time", headers=h, json={"lead_time_dias": 4, "motivo": "acordo"})
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