"""Documento de recebimento (REC-001): conferência parcial e recebimentos múltiplos."""
from __future__ import annotations

from catalog_server import auth_token, permissao
from catalog_server.app_factory import create_app
from catalog_server.db import system_conn
from catalog_server.repositories import estoque_repo
from catalog_server.repositories.compras_avancado import solicitacao_repo
from catalog_server.services import cotacao_necessidade, comparacao, pedido_compra, recebimento


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


def _pedido_recebivel(system_db) -> tuple[int, int]:
    solic = _usuario("rec_sol")
    aprov = _usuario("rec_apr")
    with system_conn() as conn:
        pid = int(conn.execute(
            "INSERT INTO produtos_cadastro (nome, ativo, sku, preco, custo_unitario) VALUES (%s,%s,%s,%s,%s) RETURNING id",
            ("P", 1, "REC-1", 10.0, 5.0),
        ).fetchone()["id"])
        conn.execute("INSERT INTO fornecedores (nome, whatsapp) VALUES (%s,%s)", ("F1", "1"))
        f1 = int(conn.execute("SELECT lastval()").fetchone()["lastval"])
        conn.execute("INSERT INTO fornecedor_preferencial (produto_id, fornecedor_id, ranking) VALUES (%s,%s,1)", (pid, f1))
        did = int(conn.execute("SELECT id FROM depositos ORDER BY id LIMIT 1").fetchone()["id"])
        conn.commit()
    sc = solicitacao_repo.create("SOL-REC", usuario_id=solic)
    solicitacao_repo.add_item(sc, pid, 10)
    solicitacao_repo.transicionar(sc, "enviada", solic)
    solicitacao_repo.transicionar(sc, "aprovada", aprov)
    cot_id = cotacao_necessidade.gerar_cotacao(sc)["cotacao_id"]
    with system_conn() as conn:
        citem = conn.execute("SELECT id FROM cotacao_itens WHERE cotacao_id=%s", (cot_id,)).fetchone()["id"]
        conn.execute(
            "INSERT INTO cotacao_precos (cotacao_item_id, fornecedor_id, preco_unitario, desconto, disponibilidade_estoque)"
            " VALUES (%s,%s,8.0,0,1)", (citem, f1),
        )
        p1 = int(conn.execute("SELECT lastval()").fetchone()["lastval"])
        conn.commit()
    comparacao.decidir_vencedor(p1, "melhor")
    pedido = pedido_compra.gerar_pedido(cot_id)["pedidos"][0]
    pedido_compra.transicionar(pedido, "aprovado")
    pedido_compra.transicionar(pedido, "enviado")
    return pedido, did


def test_criar_recebimento_retry_idempotente(system_db):
    pedido, did = _pedido_recebivel(system_db)
    r1 = recebimento.criar(pedido, did, "NF-100")
    assert r1["duplicado"] is False
    r2 = recebimento.criar(pedido, did, "NF-100")
    assert r2["duplicado"] is True
    assert r2["recebimento_id"] == r1["recebimento_id"]
    det = recebimento.detalhe(r1["recebimento_id"])
    assert len(det["itens"]) == 1
    assert float(det["itens"][0]["qtd_pedido"]) == 10.0


def test_conferencia_parcial_nao_excede_saldo(system_db):
    pedido, did = _pedido_recebivel(system_db)
    r = recebimento.criar(pedido, did, "NF-101")
    item = recebimento.detalhe(r["recebimento_id"])["itens"][0]
    # recebe 6 do pedido de 10
    recebimento.conferir_item(r["recebimento_id"], item["id"], qtd_aceita=6)
    # segundo recebimento tenta mais 6 → excede 10
    r2 = recebimento.criar(pedido, did, "NF-102")
    item2 = recebimento.detalhe(r2["recebimento_id"])["itens"][0]
    recebimento.conferir_item(r2["recebimento_id"], item2["id"], qtd_aceita=4)  # 6+4=10 ok
    r3 = recebimento.criar(pedido, did, "NF-102B")
    item3 = recebimento.detalhe(r3["recebimento_id"])["itens"][0]
    try:
        recebimento.conferir_item(r3["recebimento_id"], item3["id"], qtd_aceita=5)
        assert False, "exceder o saldo do pedido deveria falhar"
    except ValueError as exc:
        assert "excede" in str(exc)


def test_finalizar_entra_estoque_e_contas(system_db):
    pedido, did = _pedido_recebivel(system_db)
    r = recebimento.criar(pedido, did, "NF-103")
    item = recebimento.detalhe(r["recebimento_id"])["itens"][0]
    recebimento.conferir_item(r["recebimento_id"], item["id"], qtd_aceita=10)
    res = recebimento.finalizar(r["recebimento_id"])
    assert res["pedido_status"] == "recebido"
    assert res["total"] == 80.0  # 10 × 8.0
    saldo = estoque_repo.saldo(deposito_id=did, produto_id=item["produto_id"])[0]
    assert float(saldo["quantidade"]) == 10.0
    with system_conn() as conn:
        cps = conn.execute("SELECT COUNT(*) AS n FROM contas_pagar WHERE origem_tipo='pedido_compra'").fetchone()
    assert cps["n"] >= 1


def test_pedido_parcial_status(system_db):
    pedido, did = _pedido_recebivel(system_db)
    r1 = recebimento.criar(pedido, did, "NF-104")
    item1 = recebimento.detalhe(r1["recebimento_id"])["itens"][0]
    recebimento.conferir_item(r1["recebimento_id"], item1["id"], qtd_aceita=4)
    recebimento.finalizar(r1["recebimento_id"])
    with system_conn() as conn:
        st = conn.execute("SELECT status FROM pedidos_compra WHERE id=%s", (pedido,)).fetchone()
    assert st["status"] == "parcialmente_recebido"
    # segundo recebimento completa
    r2 = recebimento.criar(pedido, did, "NF-105")
    item2 = recebimento.detalhe(r2["recebimento_id"])["itens"][0]
    recebimento.conferir_item(r2["recebimento_id"], item2["id"], qtd_aceita=6)
    recebimento.finalizar(r2["recebimento_id"])
    with system_conn() as conn:
        st = conn.execute("SELECT status FROM pedidos_compra WHERE id=%s", (pedido,)).fetchone()
    assert st["status"] == "recebido"


def test_recebimento_cancelado_rejeita(system_db):
    pedido, did = _pedido_recebivel(system_db)
    pedido_compra.cancelar(pedido, "não comprar")
    try:
        recebimento.criar(pedido, did, "NF-106")
        assert False
    except ValueError as exc:
        assert "cancelado" in str(exc)


def test_api_recebimento(system_db):
    pedido, did = _pedido_recebivel(system_db)
    uid = _usuario("rec_api")
    with system_conn() as conn:
        conn.execute(
            "INSERT INTO usuario_perfis (usuario_id, perfil_id) SELECT %s, id FROM perfis WHERE nome='Administrador'",
            (uid,),
        )
        conn.commit()
    permissao.invalidar(uid)
    client = create_app().test_client()
    h = {"Authorization": f"Bearer {auth_token.criar_token({'id': uid, 'login': 'rec_api'})}"}
    r = client.post(f"/api/compras/pedidos/{pedido}/recebimentos", headers=h, json={"deposito_id": did, "documento_fiscal": "NF-API"})
    assert r.status_code == 200, r.get_json()
    rid = r.get_json()["recebimento_id"]
    item = client.get(f"/api/compras/recebimentos/{rid}", headers=h).get_json()["itens"][0]
    r = client.post(f"/api/compras/recebimentos/{rid}/itens/{item['id']}/conferir", headers=h, json={"qtd_aceita": 10})
    assert r.status_code == 200
    r = client.post(f"/api/compras/recebimentos/{rid}/finalizar", headers=h, json={})
    assert r.status_code == 200
    assert client.get("/api/compras/recebimentos", headers=h).status_code == 200