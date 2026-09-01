"""Postagem transacional idempotente (REC-005) e devolução ao fornecedor (REC-006)."""
from __future__ import annotations

from catalog_server import auth_token, permissao
from catalog_server.app_factory import create_app
from catalog_server.db import system_conn
from catalog_server.repositories import estoque_repo
from catalog_server.repositories.compras_avancado import solicitacao_repo
from catalog_server.services import cotacao_necessidade, comparacao, pedido_compra, recebimento, devolucao


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


def _setup_rec(system_db, sku: str = "DV-1") -> tuple[int, int, int, int]:
    solic = _usuario("dv_sol")
    aprov = _usuario("dv_apr")
    with system_conn() as conn:
        pid = int(conn.execute(
            "INSERT INTO produtos_cadastro (nome, ativo, sku, preco, custo_unitario, unidade_venda) VALUES (%s,%s,%s,%s,%s,%s) RETURNING id",
            ("P", 1, sku, 10.0, 5.0, "UN"),
        ).fetchone()["id"])
        conn.execute("INSERT INTO fornecedores (nome, whatsapp) VALUES (%s,%s)", ("F1", "1"))
        f1 = int(conn.execute("SELECT lastval()").fetchone()["lastval"])
        conn.execute("INSERT INTO fornecedor_preferencial (produto_id, fornecedor_id, ranking) VALUES (%s,%s,1)", (pid, f1))
        did = int(conn.execute("SELECT id FROM depositos ORDER BY id LIMIT 1").fetchone()["id"])
        conn.commit()
    sc = solicitacao_repo.create("SOL-DV", usuario_id=solic)
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
    rid = recebimento.criar(pedido, did, "NF-DV")["recebimento_id"]
    item = recebimento.detalhe(rid)["itens"][0]
    recebimento.conferir_item(rid, item["id"], 10)
    return rid, pid, did, pedido


def _finalizar(rid):
    return recebimento.finalizar(rid)


def test_finalizar_idempotente(system_db):
    rid, _, _, _ = _setup_rec(system_db)
    r1 = _finalizar(rid)
    assert r1["duplicado"] is not True
    r2 = _finalizar(rid)
    assert r2["duplicado"] is True
    assert r2["pedido_status"] == r1["pedido_status"]
    # estoque não duplica (idempotência)
    with system_conn() as conn:
        n = conn.execute("SELECT COUNT(*) FROM estoque_movimento WHERE origem_tipo='pedido_compra'").fetchone()
    assert n["count"] == 1


def test_postagem_auditada(system_db):
    rid, _, _, _ = _setup_rec(system_db)
    r = _finalizar(rid)
    with system_conn() as conn:
        row = conn.execute("SELECT * FROM recebimento_postagem WHERE recebimento_id=%s", (rid,)).fetchone()
    assert row is not None
    assert row["pedido_status"] == r["pedido_status"]
    assert row["estoque_itens"] == 1
    assert row["contas_criadas"] == 1


def test_criar_devolucao_e_concluir(system_db):
    rid, pid, did, _ = _setup_rec(system_db)
    _finalizar(rid)
    d = devolucao.criar(rid, "avariado", "avariado", "NF-DV-RET", itens=[{"produto_id": pid, "quantidade": 2}])
    assert d["itens"] == 1
    res = devolucao.concluir(d["devolucao_id"])
    assert res["total_creditado"] == 16.0  # 2 × 8.0
    # estoque saiu
    saldo = estoque_repo.saldo(deposito_id=did, produto_id=pid)[0]
    assert float(saldo["quantidade"]) == 8.0
    # crédito a pagar
    with system_conn() as conn:
        c = conn.execute("SELECT valor FROM contas_pagar WHERE origem_tipo='devolucao_fornecedor'").fetchone()
    assert float(c["valor"]) == -16.0


def test_nao_devolve_mais_que_recebido(system_db):
    rid, pid, _, _ = _setup_rec(system_db)
    _finalizar(rid)
    try:
        devolucao.criar(rid, "erro_quantidade", itens=[{"produto_id": pid, "quantidade": 11}])
        assert False, "devolver mais que o recebido deveria falhar"
    except ValueError as exc:
        assert "mais que o recebido" in str(exc)


def test_devolucao_requer_recebimento_finalizado(system_db):
    rid, pid, _, _ = _setup_rec(system_db)
    # não finalizou
    try:
        devolucao.criar(rid, "avariado", itens=[{"produto_id": pid, "quantidade": 1}])
        assert False
    except ValueError as exc:
        assert "finalizado" in str(exc)


def test_lote_rastreado_na_devolucao(system_db):
    rid, pid, _, _ = _setup_rec(system_db)
    _finalizar(rid)
    # cria lote
    from catalog_server.services import lote_rastreabilidade
    lote_id = lote_rastreabilidade.criar_lote(1, pid, "L-DV", quantidade=100)
    d = devolucao.criar(rid, "nao_conforme", itens=[{"produto_id": pid, "quantidade": 1, "lote_id": lote_id}])
    det = devolucao.detalhe(d["devolucao_id"])
    assert det["itens"][0]["lote"] == "L-DV"
    devolucao.concluir(d["devolucao_id"])


def test_api_devolucao(system_db):
    rid, pid, _, _ = _setup_rec(system_db)
    _finalizar(rid)
    uid = _usuario("dv_api")
    with system_conn() as conn:
        conn.execute(
            "INSERT INTO usuario_perfis (usuario_id, perfil_id) SELECT %s, id FROM perfis WHERE nome='Administrador'",
            (uid,),
        )
        conn.commit()
    permissao.invalidar(uid)
    client = create_app().test_client()
    h = {"Authorization": f"Bearer {auth_token.criar_token({'id': uid, 'login': 'dv_api'})}"}
    r = client.post(f"/api/compras/recebimentos/{rid}/devolucoes", headers=h,
                    json={"motivo": "avariado", "itens": [{"produto_id": pid, "quantidade": 3}]})
    assert r.status_code == 201, r.get_json()
    dev_id = r.get_json()["devolucao_id"]
    assert client.get("/api/compras/devolucoes", headers=h).status_code == 200
    r = client.post(f"/api/compras/devolucoes/{dev_id}/concluir", headers=h, json={})
    assert r.status_code == 200