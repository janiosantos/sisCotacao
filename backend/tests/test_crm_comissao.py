"""CRM/oportunidade (POS-004) e comissões (POS-005)."""
from __future__ import annotations

from catalog_server import auth_token, permissao
from catalog_server.app_factory import create_app
from catalog_server.db import system_conn
from catalog_server.services import crm_comissao


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


def _venda(system_db, vendedor_id: int) -> int:
    with system_conn() as conn:
        cid = int(conn.execute("INSERT INTO clientes (nome, doc, tipo_pessoa) VALUES (%s,%s,%s) RETURNING id", ("C", "1", "F")).fetchone()["id"])
        oid = int(conn.execute(
            "INSERT INTO orcamentos (cliente_id, numero, status, cliente, total, desconto, usuario_id, criado_em)"
            " VALUES (%s,%s,'recebido',%s,1000.0,100.0,%s,'2026-08-10 10:00:00') RETURNING id",
            (cid, "CM-1", "Cliente", vendedor_id),
        ).fetchone()["id"])
        conn.commit()
        return oid


def test_criar_oportunidade(system_db):
    uid = _usuario("crm_v")
    r = crm_comissao.criar_oportunidade(1, uid, "Obra Predial", 50000, proxima_acao="enviar proposta", proximo_contato="2026-09-10")
    assert r["status"] == "aberta"
    ops = crm_comissao.listar_oportunidades(vendedor_id=uid)
    assert any(o["id"] == r["id"] for o in ops)


def test_perdida_exige_motivo(system_db):
    r = crm_comissao.criar_oportunidade(1, None, "Proposta X", 100)
    try:
        crm_comissao.atualizar_oportunidade(r["id"], "perdida")
        assert False
    except ValueError as exc:
        assert "motivo" in str(exc)
    crm_comissao.atualizar_oportunidade(r["id"], "perdida", "preço alto")
    ops = crm_comissao.listar_oportunidades(status="perdida")
    assert any(o["id"] == r["id"] for o in ops)


def test_apurar_comissao(system_db):
    vend = _usuario("com_v")
    oid = _venda(system_db, vend)
    with system_conn() as conn:
        conn.execute("INSERT INTO comissao_politica (vendedor_id, percentual, versao) VALUES (%s,5.0,1)", (vend,))
        conn.commit()
    r = crm_comissao.apurar_venda(oid, vend)
    assert r["base"] == 900.0  # total 1000 − desconto 100
    assert r["percentual"] == 5.0
    assert r["valor"] == 45.0
    assert r["comissao_id"] is not None


def test_reverter_nao_edita(system_db):
    vend = _usuario("com_v2")
    oid = _venda(system_db, vend)
    with system_conn() as conn:
        conn.execute("INSERT INTO comissao_politica (vendedor_id, percentual, versao) VALUES (%s,5.0,1)", (vend,))
        conn.commit()
    crm_comissao.apurar_venda(oid, vend)
    r = crm_comissao.reverter(oid, "devolução")
    assert r["revertidas"] == 1
    coms = crm_comissao.listar_comissoes(status="revertida")
    assert any(c["orcamento_id"] == oid for c in coms)


def test_api_pos004_005(system_db):
    vend = _usuario("crm_api")
    oid = _venda(system_db, vend)
    uid = _usuario("crm_admin")
    with system_conn() as conn:
        conn.execute(
            "INSERT INTO usuario_perfis (usuario_id, perfil_id) SELECT %s, id FROM perfis WHERE nome='Administrador'",
            (uid,),
        )
        conn.commit()
    permissao.invalidar(uid)
    client = create_app().test_client()
    h = {"Authorization": f"Bearer {auth_token.criar_token({'id': uid, 'login': 'crm_admin'})}"}
    r = client.post("/api/posvenda/oportunidades", headers=h, json={"vendedor_id": vend, "titulo": "Obra", "valor": 1000})
    assert r.status_code == 201, r.get_json()
    op_id = r.get_json()["id"]
    r = client.patch(f"/api/posvenda/oportunidades/{op_id}", headers=h, json={"status": "perdida", "motivo_perda": "preço"})
    assert r.status_code == 200
    assert client.get("/api/posvenda/oportunidades", headers=h).status_code == 200
    r = client.post(f"/api/posvenda/comissoes/apurar/{oid}", headers=h, json={"vendedor_id": vend})
    assert r.status_code == 200
    assert client.get("/api/posvenda/comissoes", headers=h).status_code == 200