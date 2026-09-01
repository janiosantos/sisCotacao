"""Cotação a partir de necessidade (COM-008): idempotente, origem rastreável, sem duplicar item."""
from __future__ import annotations

from catalog_server import auth_token, permissao
from catalog_server.app_factory import create_app
from catalog_server.db import system_conn
from catalog_server.repositories.compras_avancado import solicitacao_repo
from catalog_server.services import cotacao_necessidade


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


def _solicitacao_aprovada(system_db) -> tuple[int, int]:
    solic = _usuario("cot_sol")
    aprov = _usuario("cot_apr")
    with system_conn() as conn:
        pid = int(conn.execute(
            "INSERT INTO produtos_cadastro (nome, ativo, sku, preco) VALUES (%s,%s,%s,%s) RETURNING id",
            ("P", 1, "C-1", 10.0),
        ).fetchone()["id"])
        conn.execute("INSERT INTO fornecedores (nome, whatsapp) VALUES (%s,%s)", ("Fornecedor", "55"))
        fid = int(conn.execute("SELECT lastval()").fetchone()["lastval"])
        conn.execute("INSERT INTO fornecedor_preferencial (produto_id, fornecedor_id, ranking) VALUES (%s,%s,1)", (pid, fid))
        conn.commit()
    sc = solicitacao_repo.create("SOL-COT", usuario_id=solic)
    solicitacao_repo.add_item(sc, pid, 20, unidade="CX")
    solicitacao_repo.transicionar(sc, "enviada", solic)
    solicitacao_repo.transicionar(sc, "aprovada", aprov)
    return sc, pid


def test_gerar_cotacao_idempotente(system_db):
    sc, pid = _solicitacao_aprovada(system_db)
    r1 = cotacao_necessidade.gerar_cotacao(sc)
    assert r1["duplicado"] is False
    assert r1["itens"] == 1
    r2 = cotacao_necessidade.gerar_cotacao(sc)
    assert r2["duplicado"] is True
    assert r2["cotacao_id"] == r1["cotacao_id"]
    with system_conn() as conn:
        row = conn.execute("SELECT status FROM solicitacao_compra WHERE id=%s", (sc,)).fetchone()
    assert row["status"] == "cotando"


def test_origem_rastreavel(system_db):
    sc, pid = _solicitacao_aprovada(system_db)
    r = cotacao_necessidade.gerar_cotacao(sc)
    with system_conn() as conn:
        row = conn.execute("SELECT solicitacao_id FROM cotacoes WHERE id=%s", (r["cotacao_id"],)).fetchone()
        item = conn.execute("SELECT solicitacao_item_id FROM cotacao_itens WHERE cotacao_id=%s", (r["cotacao_id"],)).fetchone()
    assert row["solicitacao_id"] == sc
    assert item["solicitacao_item_id"] is not None


def test_solicitacao_nao_aprovada_rejeita(system_db):
    solic = _usuario("cot_sol2")
    sc = solicitacao_repo.create("SOL-NAO", usuario_id=solic)
    try:
        cotacao_necessidade.gerar_cotacao(sc)
        assert False, "solicitação rascunho não deveria cotar"
    except ValueError:
        pass


def test_sem_itens_rejeita(system_db):
    solic = _usuario("cot_sol3")
    aprov = _usuario("cot_apr3")
    sc = solicitacao_repo.create("SOL-VAZIA", usuario_id=solic)
    try:
        cotacao_necessidade.gerar_cotacao(sc)
        assert False, "solicitação rascunho deveria falhar antes (não cotável)"
    except ValueError as exc:
        assert "não está pronta" in str(exc) or "Sem itens" in str(exc)


def test_buscar_propostas(system_db):
    sc, pid = _solicitacao_aprovada(system_db)
    r = cotacao_necessidade.gerar_cotacao(sc)
    info = cotacao_necessidade.buscar_propostas_por_produto(r["cotacao_id"])
    assert len(info["sem_proposta"]) == 1  # ainda sem proposta
    assert info["sem_proposta"][0]["produto_id"] == pid


def test_api_cotar(system_db):
    sc, pid = _solicitacao_aprovada(system_db)
    uid = _usuario("cot_api")
    with system_conn() as conn:
        conn.execute(
            "INSERT INTO usuario_perfis (usuario_id, perfil_id) SELECT %s, id FROM perfis WHERE nome='Administrador'",
            (uid,),
        )
        conn.commit()
    permissao.invalidar(uid)
    client = create_app().test_client()
    h = {"Authorization": f"Bearer {auth_token.criar_token({'id': uid, 'login': 'cot_api'})}"}
    r = client.post(f"/api/solicitacoes-compra/{sc}/cotar", headers=h, json={})
    assert r.status_code == 200, r.get_json()
    cot_id = r.get_json()["cotacao_id"]
    r = client.get(f"/api/cotacoes/{cot_id}/propostas", headers=h)
    assert r.status_code == 200
    assert len(r.get_json()["sem_proposta"]) == 1