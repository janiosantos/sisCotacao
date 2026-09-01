"""Alçada de aprovação de compra (COM-010)."""
from __future__ import annotations

from catalog_server import auth_token, permissao
from catalog_server.app_factory import create_app
from catalog_server.db import system_conn
from catalog_server.services import alcada_compra as alc


def _perfil(conn, nome: str) -> int:
    return int(conn.execute("SELECT id FROM perfis WHERE nome=%s", (nome,)).fetchone()["id"])


def _criar_perfil(conn, nome: str) -> int:
    conn.execute("INSERT INTO perfis (nome, descricao) VALUES (%s,%s)", (nome, ""))
    return int(conn.execute("SELECT lastval()").fetchone()["lastval"])


def _usuario(login: str, perfil: str) -> int:
    from werkzeug.security import generate_password_hash

    with system_conn() as conn:
        cur = conn.execute(
            "INSERT INTO usuarios (nome, login, senha_hash) VALUES (%s,%s,%s)",
            ("Op", login, generate_password_hash("x")),
        )
        uid = int(cur.lastrowid)
        conn.execute("INSERT INTO usuario_perfis (usuario_id, perfil_id) VALUES (%s,%s)", (uid, _perfil(conn, perfil)))
        conn.commit()
    return uid


def test_limite_por_perfil(system_db):
    with system_conn() as conn:
        pid = _criar_perfil(conn, "Comprador")
        alc.criar_regra(pid, 5000.0)
        conn.commit()
    uid = _usuario("alc_vend", "Comprador")
    assert alc.limite_usuario(uid) == 5000.0
    # total acima do limite → precisa aprovação
    assert alc.precisa_aprovacao(uid, 6000.0) is True
    assert alc.precisa_aprovacao(uid, 4000.0) is False


def test_sem_alcada_nao_aprova(system_db):
    uid = _usuario("alc_sem", "Vendedor")
    assert alc.limite_usuario(uid) == 0.0
    assert alc.precisa_aprovacao(uid, 10.0) is True  # 10 > 0


def test_aprovacao_rejeicao(system_db):
    aprov = _usuario("alc_apr", "Administrador")
    r = alc.registrar_aprovacao(1, aprov, "aprovado", "dentro da política", {"total": 100}, {"total": 100})
    assert r["status"] == "aprovado"
    assert alc.aprovado_vigente(1) is True
    alc.registrar_aprovacao(1, aprov, "rejeitado", "acima do orçamento")
    assert alc.aprovado_vigente(1) is False


def test_invalidar_por_alteracao(system_db):
    aprov = _usuario("alc_apr2", "Administrador")
    alc.registrar_aprovacao(2, aprov, "aprovado", "ok", {"total": 100}, {"total": 100}, versao=1)
    alc.invalidar_aprovacao(2, aprov, "total alterado para 150")
    assert alc.aprovado_vigente(2) is False
    ult = alc.ultima_aprovacao(2)
    assert ult["status"] == "invalidado"
    assert ult["versao"] == 2


def test_api_alcada(system_db):
    with system_conn() as conn:
        pid = _criar_perfil(conn, "Comprador")
        conn.commit()
    uid = _usuario("alc_api", "Administrador")
    permissao.invalidar(uid)
    client = create_app().test_client()
    h = {"Authorization": f"Bearer {auth_token.criar_token({'id': uid, 'login': 'alc_api'})}"}
    r = client.get("/api/alcada-compra", headers=h)
    assert r.status_code == 200
    r = client.post("/api/alcada-compra", headers=h, json={"perfil_id": pid, "limite_valor": 10000})
    assert r.status_code == 201
    r = client.get(f"/api/alcada-compra/verificar?usuario_id={uid}&total=15000", headers=h)
    assert r.status_code == 200
    assert r.get_json()["precisa_aprovacao"] is True
    r = client.post("/api/alcada-compra/aprovacoes", headers=h, json={"pedido_id": 9, "aprovador_id": uid, "status": "aprovado", "motivo": "ok"})
    assert r.status_code == 200