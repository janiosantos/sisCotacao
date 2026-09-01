"""Pós-venda (POS-001/002): RMA, troca e crédito de cliente."""
from __future__ import annotations

from catalog_server import auth_token, permissao
from catalog_server.app_factory import create_app
from catalog_server.db import system_conn
from catalog_server.repositories import estoque_repo
from catalog_server.services import posvenda


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


def _venda(system_db) -> tuple[int, int, int]:
    with system_conn() as conn:
        cid = int(conn.execute("INSERT INTO clientes (nome, doc, tipo_pessoa) VALUES (%s,%s,%s) RETURNING id", ("C", "1", "F")).fetchone()["id"])
        pid = int(conn.execute(
            "INSERT INTO produtos_cadastro (nome, ativo, sku, preco, custo_unitario) VALUES (%s,%s,%s,%s,%s) RETURNING id",
            ("P", 1, "POS-1", 10.0, 5.0),
        ).fetchone()["id"])
        oid = int(conn.execute(
            "INSERT INTO orcamentos (cliente_id, numero, status, cliente, total, criado_em)"
            " VALUES (%s,%s,'recebido',%s,100.0,'2026-08-10 10:00:00') RETURNING id",
            (cid, "POS-O1", "Cliente"),
        ).fetchone()["id"])
        conn.execute(
            "INSERT INTO orcamento_itens (orcamento_id, produto_id, nome, quantidade, preco_unitario, subtotal)"
            " VALUES (%s,%s,%s,10,10.0,100.0)", (oid, pid, "P"),
        )
        did = int(conn.execute("SELECT id FROM depositos ORDER BY id LIMIT 1").fetchone()["id"])
        conn.commit()
    estoque_repo.movimentar_fato(did, pid, "entrada", 10, custo_unitario=5.0, origem_tipo="teste")
    estoque_repo.movimentar_fato(did, pid, "saida", 10, custo_unitario=5.0, origem_tipo="venda", origem_id=oid)
    return oid, pid, did


def test_solicitar_rma(system_db):
    oid, pid, _ = _venda(system_db)
    r = posvenda.solicitar(oid, pid, 2, "defeito")
    assert r["status"] == "solicitada"


def test_devolucao_acima_vendido_bloqueada(system_db):
    oid, pid, _ = _venda(system_db)
    try:
        posvenda.solicitar(oid, pid, 11, "defeito")
        assert False
    except ValueError as exc:
        assert "acima do vendido" in str(exc)


def test_fluxo_completo_e_credito(system_db):
    oid, pid, did = _venda(system_db)
    r = posvenda.solicitar(oid, pid, 2, "arrependimento", condicao="novo")
    rid = r["rma_id"]
    posvenda.transicionar(rid, "autorizada")
    posvenda.transicionar(rid, "recebida")
    posvenda.transicionar(rid, "analisada")
    res = posvenda.transicionar(rid, "concluida", "defeito confirmado")
    assert res["status"] == "concluida"
    # estoque reposto (2 unidades de volta)
    saldo = estoque_repo.saldo(deposito_id=did, produto_id=pid)[0]
    assert float(saldo["quantidade"]) == 2.0
    # crédito de cliente gerado (2 × 10 = 20)
    cred = posvenda.credito_cliente(1)
    assert cred["saldo"] == 20.0


def test_transicao_invalida(system_db):
    oid, pid, _ = _venda(system_db)
    r = posvenda.solicitar(oid, pid, 1, "defeito")
    try:
        posvenda.transicionar(r["rma_id"], "concluida")
        assert False
    except ValueError:
        pass


def test_troca_com_diferenca(system_db):
    oid, pid, _ = _venda(system_db)
    r = posvenda.solicitar(oid, pid, 2, "defeito")
    posvenda.transicionar(r["rma_id"], "autorizada")
    # produto novo mais caro → estorno; mais barato → crédito
    res = posvenda.trocar(r["rma_id"], 999, 1, 15.0)  # 15 vs original 20 (2×10)
    assert res["diferenca"] == -5.0
    assert res["credito_ou_estorno"] == "credito"


def test_api_posvenda(system_db):
    oid, pid, _ = _venda(system_db)
    uid = _usuario("pos_api")
    with system_conn() as conn:
        conn.execute(
            "INSERT INTO usuario_perfis (usuario_id, perfil_id) SELECT %s, id FROM perfis WHERE nome='Administrador'",
            (uid,),
        )
        conn.commit()
    permissao.invalidar(uid)
    client = create_app().test_client()
    h = {"Authorization": f"Bearer {auth_token.criar_token({'id': uid, 'login': 'pos_api'})}"}
    r = client.post("/api/posvenda/rma", headers=h, json={"orcamento_id": oid, "produto_id": pid, "quantidade": 2, "motivo": "defeito"})
    assert r.status_code == 201, r.get_json()
    rid = r.get_json()["rma_id"]
    r = client.post(f"/api/posvenda/rma/{rid}/status", headers=h, json={"status": "autorizada"})
    assert r.status_code == 200
    assert client.get("/api/posvenda/rma", headers=h).status_code == 200
    assert client.get("/api/posvenda/credito/1", headers=h).status_code == 200