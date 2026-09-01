"""XYZ e matriz de política (COM-002)."""
from __future__ import annotations

from catalog_server import auth_token, permissao
from catalog_server.app_factory import create_app
from catalog_server.db import system_conn
from catalog_server.services import xyz as xyz_svc


def _setup(system_db) -> int:
    with system_conn() as conn:
        conn.execute("INSERT INTO produtos_cadastro (nome, ativo, sku, preco) VALUES (%s,%s,%s,%s)", ("P", 1, "X-1", 10.0))
        pid = int(conn.execute("SELECT lastval()").fetchone()["lastval"])
        cid = int(conn.execute("INSERT INTO clientes (nome, doc, tipo_pessoa) VALUES (%s,%s,%s) RETURNING id", ("C", "1", "F")).fetchone()["id"])
        # vendas estáveis (X): 10 un em cada um dos últimos 6 meses
        meses = [r["mes"] for r in conn.execute(
            "SELECT to_char(generate_series(CURRENT_DATE - (6::int * interval '1 month') + interval '1 day', CURRENT_DATE, interval '1 month'), 'YYYY-MM') AS mes"
        ).fetchall()]
        for i, mes in enumerate(meses, start=1):
            oid = int(conn.execute(
                "INSERT INTO orcamentos (cliente_id, numero, status, criado_em) VALUES (%s,%s,%s,%s) RETURNING id",
                (cid, f"O-{i}", "finalizado", f"{mes}-15 10:00:00"),
            ).fetchone()["id"])
            conn.execute(
                "INSERT INTO orcamento_itens (orcamento_id, produto_id, nome, quantidade, preco_unitario, subtotal)"
                " VALUES (%s,%s,%s,%s,%s,%s)", (oid, pid, "X", 10, 10.0, 100.0),
            )
        conn.commit()
        return pid


def test_classificar_estavel_x(system_db):
    pid = _setup(system_db)
    r = xyz_svc.classificar(pid)
    assert r["classe_xyz"] == "X"
    assert r["intermitente"] is False
    assert r["cv"] == 0.0


def test_matriz_politica():
    assert xyz_svc.matriz_politica("A", "X")["servico"] == "alto"
    assert xyz_svc.matriz_politica("C", "Z")["estoque"] == "sob encomenda"


def test_config_update(system_db):
    cfg = xyz_svc.atualizar_config(0.3, 0.8, 4, 0.6, None)
    assert float(cfg["cv_x"]) == 0.3
    assert cfg["meses_historico"] == 4
    cfg2 = xyz_svc._config()
    assert float(cfg2["cv_y"]) == 0.8


def test_resumo_matriz(system_db):
    pid = _setup(system_db)
    xyz_svc.classificar(pid)
    with system_conn() as conn:
        conn.execute("UPDATE produtos_cadastro SET classe_abc='A' WHERE id=%s", (pid,))
        conn.commit()
    r = xyz_svc.resumo_matriz()
    assert any(c["abc"] == "A" and c["xyz"] == "X" for c in r["celulas"])


def test_api_xyz_fluxo(system_db):
    pid = _setup(system_db)
    uid = _usuario("xyzr")
    with system_conn() as conn:
        conn.execute(
            "INSERT INTO usuario_perfis (usuario_id, perfil_id) SELECT %s, id FROM perfis WHERE nome='Administrador'",
            (uid,),
        )
        conn.commit()
    permissao.invalidar(uid)
    client = create_app().test_client()
    h = {"Authorization": f"Bearer {auth_token.criar_token({'id': uid, 'login': 'xyzr'})}"}
    r = client.post("/api/estoque/xyz/calcular", headers=h, json={"produto_id": pid})
    assert r.status_code == 200, r.get_json()
    assert r.get_json()["resultado"]["classe_xyz"] == "X"
    assert client.get("/api/estoque/xyz/config", headers=h).status_code == 200
    r = client.put("/api/estoque/xyz/config", headers=h, json={"cv_x": 0.4, "cv_y": 0.9, "meses_historico": 6, "intermitente_zeros_pct": 0.5})
    assert r.status_code == 200
    assert client.get("/api/estoque/xyz/matriz", headers=h).status_code == 200


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