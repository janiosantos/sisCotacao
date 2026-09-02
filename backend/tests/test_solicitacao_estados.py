"""Solicitação de compra (COM-007): máquina de estados e bloqueio de edição."""
from __future__ import annotations

from catalog_server import auth_token, permissao
from catalog_server.app_factory import create_app
from catalog_server.db import system_conn
from catalog_server.repositories.compras_avancado import solicitacao_repo


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


def _produto(system_db) -> int:
    with system_conn() as conn:
        pid = int(conn.execute(
            "INSERT INTO produtos_cadastro (nome, ativo, sku, preco) VALUES (%s,%s,%s,%s) RETURNING id",
            ("P", 1, "S-1", 10.0),
        ).fetchone()["id"])
        conn.commit()
        return pid


def test_criar_com_campos_novos(system_db):
    sc = solicitacao_repo.create("SOL-1", "Repor", prioridade="alta", origem="sugestao",
                                 centro_custo="LOJA-01", deposito_id=1, prazo_desejado="2026-10-01")
    det = solicitacao_repo.get(sc)
    assert det["prioridade"] == "alta"
    assert det["origem"] == "sugestao"
    assert det["centro_custo"] == "LOJA-01"


def test_transicao_completa(system_db):
    solic = _usuario("sol1")
    aprov = _usuario("apr1")
    sc = solicitacao_repo.create("SOL-2")
    r = solicitacao_repo.transicionar(sc, "enviada", solic)
    assert r["para"] == "enviada"
    r = solicitacao_repo.transicionar(sc, "aprovada", aprov)
    assert r["para"] == "aprovada"
    assert solicitacao_repo.transicionar(sc, "cotando", aprov)["para"] == "cotando"
    assert solicitacao_repo.transicionar(sc, "convertida", aprov)["para"] == "convertida"


def test_transicao_invalida(system_db):
    sc = solicitacao_repo.create("SOL-3")
    try:
        solicitacao_repo.transicionar(sc, "aprovada", 5)
        assert False, "rascunho→aprovada deveria ser inválida"
    except ValueError:
        pass
    # enviada → cotando (pula aprovação) também é inválida
    solicitacao_repo.transicionar(sc, "enviada", 1)
    try:
        solicitacao_repo.transicionar(sc, "cotando", 5)
        assert False
    except ValueError:
        pass


def test_aprovador_nao_pode_ser_solicitante(system_db):
    solic = _usuario("sol2")
    sc = solicitacao_repo.create("SOL-4", usuario_id=solic)
    solicitacao_repo.transicionar(sc, "enviada", solic)
    try:
        solicitacao_repo.transicionar(sc, "aprovada", solic)
        assert False, "aprovador = solicitante deveria falhar"
    except ValueError:
        pass


def test_aprovada_nao_edita(system_db):
    solic = _usuario("sol3")
    aprov = _usuario("apr3")
    pid = _produto(system_db)
    sc = solicitacao_repo.create("SOL-5", usuario_id=solic)
    solicitacao_repo.add_item(sc, pid, 10)
    solicitacao_repo.transicionar(sc, "enviada", solic)
    solicitacao_repo.transicionar(sc, "aprovada", aprov)
    try:
        solicitacao_repo.add_item(sc, pid, 5)
        assert False, "item em aprovada deveria ser bloqueado"
    except ValueError as exc:
        assert "editada" in str(exc)
    try:
        solicitacao_repo.remover_item(sc, 1)
        assert False
    except ValueError:
        pass


def test_remover_item_rascunho_ok(system_db):
    pid = _produto(system_db)
    sc = solicitacao_repo.create("SOL-6")
    item = solicitacao_repo.add_item(sc, pid, 10, unidade="CX", necessidade=12, origem_sugestao="motor")
    assert solicitacao_repo.remover_item(sc, item) is True
    assert len(solicitacao_repo.get(sc)["itens"]) == 0


def test_cancelada_nao_transiciona(system_db):
    sc = solicitacao_repo.create("SOL-7")
    solicitacao_repo.transicionar(sc, "cancelada", 1)
    try:
        solicitacao_repo.transicionar(sc, "enviada", 1)
        assert False
    except ValueError:
        pass


def test_api_fluxo(system_db):
    solic = _usuario("apisol")
    aprov = _usuario("apiapr")
    with system_conn() as conn:
        conn.execute(
            "INSERT INTO usuario_perfis (usuario_id, perfil_id) SELECT %s, id FROM perfis WHERE nome='Administrador'",
            (solic,),
        )
        conn.execute(
            "INSERT INTO usuario_perfis (usuario_id, perfil_id) SELECT %s, id FROM perfis WHERE nome='Administrador'",
            (aprov,),
        )
        conn.commit()
    permissao.invalidar(solic)
    permissao.invalidar(aprov)
    client = create_app().test_client()
    h = {"Authorization": f"Bearer {auth_token.criar_token({'id': solic, 'login': 'apisol'})}"}
    h_aprov = {"Authorization": f"Bearer {auth_token.criar_token({'id': aprov, 'login': 'apiapr'})}"}
    r = client.post("/api/solicitacoes-compra", headers=h, json={"codigo": "SOL-API", "prioridade": "urgente", "origem": "sugestao"})
    assert r.status_code == 201, r.get_json()
    sc_id = r.get_json()["id"]
    r = client.post(f"/api/solicitacoes-compra/{sc_id}/transicao", headers=h, json={"status": "enviada", "usuario_id": solic})
    assert r.status_code == 200
    r = client.post(f"/api/solicitacoes-compra/{sc_id}/transicao", headers=h_aprov, json={"status": "aprovada", "usuario_id": solic})
    assert r.status_code == 200
    r = client.post(f"/api/solicitacoes-compra/{sc_id}/transicao", headers=h_aprov, json={"status": "cotando", "usuario_id": solic})
    assert r.status_code == 200
    # transição inválida
    r = client.post(f"/api/solicitacoes-compra/{sc_id}/transicao", headers=h, json={"status": "cancelada"})
    assert r.status_code == 400
