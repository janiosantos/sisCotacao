"""Sessão de caixa e terminal (VEN-004)."""
from __future__ import annotations

from catalog_server import auth_token, permissao
from catalog_server.app_factory import create_app
from catalog_server.db import system_conn
from catalog_server.repositories import caixa_repo
from catalog_server.services import caixa_sessao


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


def test_abrir_sessao(system_db):
    uid = _usuario("cx_op1")
    r = caixa_sessao.abrir(uid, 100.0, terminal="PDV-1")
    assert r["status"] == "aberta"
    det = caixa_sessao.detalhe(r["sessao_id"])
    assert det["saldo_inicial"] == 100.0
    assert len(det["movimentos"]) == 1  # abertura


def test_nao_abre_duas(system_db):
    uid = _usuario("cx_op2")
    caixa_sessao.abrir(uid, 0.0)
    try:
        caixa_sessao.abrir(uid, 50.0)
        assert False, "segunda sessão aberta deveria falhar"
    except ValueError as exc:
        assert "aberta" in str(exc)


def test_suprimento_sangria_fechamento(system_db):
    uid = _usuario("cx_op3")
    r = caixa_sessao.abrir(uid, 100.0)
    sid = r["sessao_id"]
    caixa_sessao.suprimento(sid, 50.0, "troco")
    caixa_sessao.sangria(sid, 20.0, "compra de água")
    # venda entra na sessão automaticamente (vinculo pelo operador)
    caixa_repo.movimentar("entrada", "Venda teste", 200.0, usuario_id=uid)
    fc = caixa_sessao.fechar(sid, 330.0)
    assert fc["status"] == "fechada"
    assert fc["saldo_esperado"] == 330.0  # 100 + 50 - 20 + 200
    assert fc["diferenca"] == 0.0


def test_fechada_bloqueia_movimentos(system_db):
    uid = _usuario("cx_op4")
    r = caixa_sessao.abrir(uid, 0.0)
    sid = r["sessao_id"]
    caixa_sessao.fechar(sid, 0.0)
    try:
        caixa_repo.movimentar("entrada", "depois de fechar", 10.0, usuario_id=uid)
        assert False, "movimento após fechamento deveria ser bloqueado"
    except ValueError as exc:
        assert "fechada" in str(exc)


def test_aprovar_diferenca(system_db):
    uid = _usuario("cx_op5")
    aprov = _usuario("cx_ap5")
    r = caixa_sessao.abrir(uid, 100.0)
    fc = caixa_sessao.fechar(r["sessao_id"], 95.0, "faltou 5")
    assert fc["diferenca"] == -5.0
    caixa_sessao.aprovar(r["sessao_id"], aprov)
    det = caixa_sessao.detalhe(r["sessao_id"])
    assert det["aprovador_id"] == aprov
    assert det["diferenca"] == -5.0


def test_api_sessao(system_db):
    uid = _usuario("cx_api")
    with system_conn() as conn:
        conn.execute(
            "INSERT INTO usuario_perfis (usuario_id, perfil_id) SELECT %s, id FROM perfis WHERE nome='Administrador'",
            (uid,),
        )
        conn.commit()
    permissao.invalidar(uid)
    client = create_app().test_client()
    h = {"Authorization": f"Bearer {auth_token.criar_token({'id': uid, 'login': 'cx_api'})}"}
    r = client.post("/api/financeiro/caixa/sessao/abrir", headers=h, json={"operador_id": uid, "saldo_inicial": 50})
    assert r.status_code == 200, r.get_json()
    sid = r.get_json()["sessao_id"]
    r = client.post(f"/api/financeiro/caixa/sessao/{sid}/suprimento", headers=h, json={"valor": 10})
    assert r.status_code == 200
    assert client.get("/api/financeiro/caixa/sessao", headers=h).status_code == 200
    assert client.get(f"/api/financeiro/caixa/sessao/{sid}", headers=h).status_code == 200
    r = client.post(f"/api/financeiro/caixa/sessao/{sid}/fechar", headers=h, json={"saldo_contado": 60})
    assert r.status_code == 200