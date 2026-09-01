"""Rastreabilidade de lote (EST-008): status, FEFO, controle por família, guard de saída e recall."""
from __future__ import annotations

from catalog_server import auth_token, permissao
from catalog_server.app_factory import create_app
from catalog_server.db import system_conn
from catalog_server.repositories import estoque_repo
from catalog_server.services import lote_rastreabilidade as lote_svc


def _setup(system_db) -> tuple[int, int]:
    with system_conn() as conn:
        conn.execute("INSERT INTO produtos_cadastro (nome, ativo, sku, preco, familia_id) VALUES (%s,%s,%s,%s,NULL)", ("P", 1, "L-1", 10.0))
        pid = int(conn.execute("SELECT lastval()").fetchone()["lastval"])
        did = int(conn.execute("SELECT id FROM depositos ORDER BY id LIMIT 1").fetchone()["id"])
        conn.commit()
        return pid, did


def test_criar_lote_entrada_ledger(system_db):
    pid, did = _setup(system_db)
    lote_id = lote_svc.criar_lote(did, pid, "L-A", quantidade=10, data_validade="2099-12-31", origem="compra", documento="NF-1", custo_unitario=5.0)
    saldo = estoque_repo.saldo(deposito_id=did, produto_id=pid)[0]
    assert float(saldo["quantidade"]) == 10.0
    with system_conn() as conn:
        row = conn.execute("SELECT origem, documento, custo_unitario, status FROM lotes WHERE id=%s", (lote_id,)).fetchone()
    assert row["origem"] == "compra"
    assert row["documento"] == "NF-1"
    assert float(row["custo_unitario"]) == 5.0


def test_fefo_ordena_por_validade(system_db):
    pid, did = _setup(system_db)
    lote_svc.criar_lote(did, pid, "L-B", quantidade=5, data_validade="2098-12-31")
    lote_svc.criar_lote(did, pid, "L-A", quantidade=5, data_validade="2099-12-31")
    aloc = lote_svc.fefo(pid, did, 7)
    assert [a["codigo"] for a in aloc] == ["L-B", "L-A"]
    assert aloc[0]["quantidade"] == 5
    assert aloc[1]["quantidade"] == 2


def test_fefo_exclui_vencido_e_bloqueado(system_db):
    pid, did = _setup(system_db)
    lote_svc.criar_lote(did, pid, "L-VENC", quantidade=5, data_validade="2020-01-01")
    lb = lote_svc.criar_lote(did, pid, "L-BLOQ", quantidade=5)
    lote_svc.atualizar_status(lb, "bloqueado")
    lote_svc.criar_lote(did, pid, "L-OK", quantidade=5, data_validade="2099-12-31")
    try:
        lote_svc.fefo(pid, did, 10)
        assert False, "vencido/bloqueado não deveriam entrar na alocação"
    except ValueError:
        pass
    aloc = lote_svc.fefo(pid, did, 5)
    assert aloc[0]["codigo"] == "L-OK"


def test_saida_lote_vencido_bloqueada(system_db):
    pid, did = _setup(system_db)
    lote_id = lote_svc.criar_lote(did, pid, "L-VENC", quantidade=5, data_validade="2020-01-01")
    try:
        estoque_repo.movimentar_fato(did, pid, "saida", 1, lote_id=lote_id, origem_tipo="venda", origem_id=1)
        assert False, "saída de lote vencido deveria falhar"
    except ValueError as exc:
        assert "vencido" in str(exc)


def test_saida_lote_valido_ok(system_db):
    pid, did = _setup(system_db)
    lote_id = lote_svc.criar_lote(did, pid, "L-OK", quantidade=5, data_validade="2099-12-31")
    r = estoque_repo.movimentar_fato(did, pid, "saida", 3, lote_id=lote_id, origem_tipo="venda", origem_id=1)
    assert float(r["saldo_posterior"]) == 2.0
    with system_conn() as conn:
        row = conn.execute("SELECT quantidade FROM lotes WHERE id=%s", (lote_id,)).fetchone()
    assert float(row["quantidade"]) == 2.0  # saldo do lote acompanha? (movimento não baixa lote — ver teste abaixo)


def test_controle_por_familia(system_db):
    pid, did = _setup(system_db)
    assert lote_svc.familia_controla_lote(pid) is False
    with system_conn() as conn:
        conn.execute("INSERT INTO familias (nome, controle_lote) VALUES (%s, TRUE)", ("Fam Controlada",))
        fid = int(conn.execute("SELECT lastval()").fetchone()["lastval"])
        conn.execute("UPDATE produtos_cadastro SET familia_id=%s WHERE id=%s", (fid, pid))
        conn.commit()
    assert lote_svc.familia_controla_lote(pid) is True


def test_recall_via_ledger(system_db):
    pid, did = _setup(system_db)
    lote_id = lote_svc.criar_lote(did, pid, "L-REC", quantidade=10, data_validade="2099-12-31")
    # cliente + orçamento + saída com lote
    with system_conn() as conn:
        conn.execute("INSERT INTO clientes (nome, doc, tipo_pessoa) VALUES (%s,%s,%s)", ("Cliente A", "123", "F"))
        cid = int(conn.execute("SELECT lastval()").fetchone()["lastval"])
        conn.execute("INSERT INTO orcamentos (cliente_id, numero, status) VALUES (%s,%s,%s)", (cid, "ORC-1", "finalizado"))
        oid = int(conn.execute("SELECT lastval()").fetchone()["lastval"])
        conn.commit()
    estoque_repo.movimentar_fato(did, pid, "saida", 2, lote_id=lote_id, origem_tipo="venda", origem_id=oid)
    r = lote_svc.recall(pid, lote_id)
    assert len(r) == 1
    assert r[0]["cliente"] == "Cliente A"
    assert int(r[0]["orcamento_id"]) == oid


def test_api_lote_fluxo(system_db):
    pid, did = _setup(system_db)
    uid = _usuario("loter")
    with system_conn() as conn:
        conn.execute(
            "INSERT INTO usuario_perfis (usuario_id, perfil_id) SELECT %s, id FROM perfis WHERE nome='Administrador'",
            (uid,),
        )
        conn.commit()
    permissao.invalidar(uid)
    client = create_app().test_client()
    h = {"Authorization": f"Bearer {auth_token.criar_token({'id': uid, 'login': 'loter'})}"}
    r = client.post("/api/estoque/lotes", headers=h, json={
        "deposito_id": did, "produto_id": pid, "codigo": "API-L", "quantidade": 6,
        "data_validade": "2099-12-31", "origem": "compra", "documento": "NF-9", "custo_unitario": 4.0,
    })
    assert r.status_code == 201, r.get_json()
    lid = r.get_json()["id"]
    r = client.get(f"/api/estoque/lotes/{lid}", headers=h)
    assert r.get_json()["origem"] == "compra"
    r = client.post(f"/api/estoque/lotes/{lid}/status", headers=h, json={"status": "bloqueado"})
    assert r.status_code == 200
    r = client.get(f"/api/estoque/lotes/fefo?produto_id={pid}&deposito_id={did}&quantidade=2", headers=h)
    assert r.status_code == 400  # bloqueado não entra no FEFO
    assert client.get(f"/api/estoque/lotes/recall?produto_id={pid}", headers=h).status_code == 200


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