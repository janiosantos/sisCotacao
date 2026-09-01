"""Transporte/entrega (INT-005) e impressão (INT-003)."""
from __future__ import annotations

from catalog_server import auth_token, permissao
from catalog_server.app_factory import create_app
from catalog_server.db import system_conn
from catalog_server.repositories import expedicao_repo
from catalog_server.services import expedicao_avancada
from catalog_server.services.impressao import impressao_service


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


def _cliente_admin(system_db):
    uid = _usuario("int_admin")
    with system_conn() as conn:
        conn.execute(
            "INSERT INTO usuario_perfis (usuario_id, perfil_id) SELECT %s, id FROM perfis WHERE nome='Administrador'",
            (uid,),
        )
        conn.commit()
    permissao.invalidar(uid)
    return create_app().test_client(), {"Authorization": f"Bearer {auth_token.criar_token({'id': uid, 'login': 'int_admin'})}"}


def _expedicao(system_db) -> int:
    with system_conn() as conn:
        did = int(conn.execute("SELECT id FROM depositos ORDER BY id LIMIT 1").fetchone()["id"])
        exp_id = expedicao_repo.create("EXP-1", did)
        conn.commit()
        return exp_id


# ─── INT-005 ───────────────────────────────────────────────

def test_criar_transportadora_e_sla(system_db):
    tr = expedicao_avancada.criar_transportadora("Transportadora X", "12345678000190", "5511", 3)
    exp = _expedicao(system_db)
    r = expedicao_avancada.definir_transporte(exp, tr, rastreio="RT-123")
    assert r["transportadora_id"] == tr
    assert r["sla_data"] is not None  # hoje + 3 dias


def test_fluxo_logistico(system_db):
    exp = _expedicao(system_db)
    assert expedicao_avancada.transicionar(exp, "separada")["para"] == "separada"
    assert expedicao_avancada.transicionar(exp, "enviada")["para"] == "enviada"
    assert expedicao_avancada.transicionar(exp, "entregue")["para"] == "entregue"
    try:
        expedicao_avancada.transicionar(exp, "separada")
        assert False, "entregue → separada é inválido"
    except ValueError:
        pass
    eventos = expedicao_avancada.listar_eventos(exp)
    assert len(eventos) >= 3


def test_entrega_parcial(system_db):
    exp = _expedicao(system_db)
    expedicao_avancada.transicionar(exp, "separada")
    expedicao_avancada.transicionar(exp, "enviada")
    assert expedicao_avancada.transicionar(exp, "parcialmente_entregue")["para"] == "parcialmente_entregue"
    assert expedicao_avancada.transicionar(exp, "entregue")["para"] == "entregue"


def test_api_transporte(system_db):
    exp = _expedicao(system_db)
    client, h = _cliente_admin(system_db)
    r = client.post("/api/estoque/transportadoras", headers=h, json={"nome": "TR", "prazo_medio_dias": 2})
    assert r.status_code == 201, r.get_json()
    tr = r.get_json()["id"]
    r = client.post(f"/api/estoque/expedicao/{exp}/transporte", headers=h, json={"transportadora_id": tr})
    assert r.status_code == 200
    r = client.post(f"/api/estoque/expedicao/{exp}/status", headers=h, json={"status": "separada"})
    assert r.status_code == 200
    r = client.post(f"/api/estoque/expedicao/{exp}/status", headers=h, json={"status": "enviada"})
    assert r.status_code == 200
    assert client.get(f"/api/estoque/expedicao/{exp}/eventos", headers=h).status_code == 200


# ─── INT-003 ───────────────────────────────────────────────

def test_reenfileirar_reimpressao_auditada(system_db):
    job = impressao_service.enfileirar({"numero": "O-1", "cliente": "C"})
    novo = impressao_service.reenfileirar(job, 1)
    assert novo > job
    fila = impressao_service.status()
    assert any(j["id"] == novo for j in fila)
    with system_conn() as conn:
        ev = conn.execute("SELECT COUNT(*) FROM auditoria_evento WHERE acao='reimpressao'").fetchone()
    assert ev["count"] == 1


def test_api_reimprimir(system_db):
    client, h = _cliente_admin(system_db)
    job = impressao_service.enfileirar({"numero": "O-2"})
    r = client.post(f"/api/impressao/fila/{job}/reimprimir", headers=h)
    assert r.status_code == 202, r.get_json()
    assert client.get("/api/impressao/fila", headers=h).status_code == 200