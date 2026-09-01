"""Pedido de compra (COM-011) e histórico (COM-012)."""
from __future__ import annotations

from catalog_server import auth_token, permissao
from catalog_server.app_factory import create_app
from catalog_server.db import system_conn
from catalog_server.repositories.compras_avancado import solicitacao_repo
from catalog_server.services import cotacao_necessidade, comparacao, pedido_compra


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


def _setup_pedido(system_db) -> tuple[int, int]:
    solic = _usuario("pc_sol")
    aprov = _usuario("pc_apr")
    with system_conn() as conn:
        pid = int(conn.execute(
            "INSERT INTO produtos_cadastro (nome, ativo, sku, preco) VALUES (%s,%s,%s,%s) RETURNING id",
            ("P", 1, "PC-1", 10.0),
        ).fetchone()["id"])
        conn.execute("INSERT INTO fornecedores (nome, whatsapp) VALUES (%s,%s)", ("F1", "1"))
        f1 = int(conn.execute("SELECT lastval()").fetchone()["lastval"])
        conn.execute("INSERT INTO fornecedor_preferencial (produto_id, fornecedor_id, ranking) VALUES (%s,%s,1)", (pid, f1))
        conn.commit()
    sc = solicitacao_repo.create("SOL-PC", usuario_id=solic)
    solicitacao_repo.add_item(sc, pid, 20)
    solicitacao_repo.transicionar(sc, "enviada", solic)
    solicitacao_repo.transicionar(sc, "aprovada", aprov)
    r = cotacao_necessidade.gerar_cotacao(sc)
    with system_conn() as conn:
        citem = conn.execute("SELECT id FROM cotacao_itens WHERE cotacao_id=%s", (r["cotacao_id"],)).fetchone()["id"]
        conn.execute(
            "INSERT INTO cotacao_precos (cotacao_item_id, fornecedor_id, preco_unitario, desconto, disponibilidade_estoque)"
            " VALUES (%s,%s,8.5,0,1)", (citem, f1),
        )
        p1 = int(conn.execute("SELECT lastval()").fetchone()["lastval"])
        conn.commit()
    comparacao.decidir_vencedor(p1, "melhor preço")
    return r["cotacao_id"], pid


def test_gerar_pedido_dos_vencedores(system_db):
    cot_id, pid = _setup_pedido(system_db)
    r = pedido_compra.gerar_pedido(cot_id)
    assert len(r["pedidos"]) == 1
    with system_conn() as conn:
        item = conn.execute("SELECT quantidade, preco_unitario FROM pedido_itens WHERE pedido_id=%s", (r["pedidos"][0],)).fetchone()
        st = conn.execute("SELECT status FROM pedidos_compra WHERE id=%s", (r["pedidos"][0],)).fetchone()
    assert float(item["quantidade"]) == 20.0
    assert float(item["preco_unitario"]) == 8.5
    assert st["status"] == "rascunho"


def test_sem_decisao_rejeita(system_db):
    solic = _usuario("pc_sol2")
    aprov = _usuario("pc_apr2")
    with system_conn() as conn:
        pid = int(conn.execute(
            "INSERT INTO produtos_cadastro (nome, ativo, sku, preco) VALUES (%s,%s,%s,%s) RETURNING id",
            ("P", 1, "PC-2", 10.0),
        ).fetchone()["id"])
        conn.execute("INSERT INTO fornecedores (nome, whatsapp) VALUES (%s,%s)", ("F1", "1"))
        f1 = int(conn.execute("SELECT lastval()").fetchone()["lastval"])
        conn.execute("INSERT INTO fornecedor_preferencial (produto_id, fornecedor_id, ranking) VALUES (%s,%s,1)", (pid, f1))
        conn.commit()
    sc = solicitacao_repo.create("SOL-PC2", usuario_id=solic)
    solicitacao_repo.add_item(sc, pid, 5)
    solicitacao_repo.transicionar(sc, "enviada", solic)
    solicitacao_repo.transicionar(sc, "aprovada", aprov)
    cot_id = cotacao_necessidade.gerar_cotacao(sc)["cotacao_id"]
    try:
        pedido_compra.gerar_pedido(cot_id)
        assert False, "sem decisão deveria falhar"
    except ValueError as exc:
        assert "decisão" in str(exc)


def test_maquina_de_estados(system_db):
    cot_id, _ = _setup_pedido(system_db)
    pedido = pedido_compra.gerar_pedido(cot_id)["pedidos"][0]
    assert pedido_compra.transicionar(pedido, "aprovado")["para"] == "aprovado"
    assert pedido_compra.transicionar(pedido, "enviado")["para"] == "enviado"
    assert pedido_compra.transicionar(pedido, "confirmado")["para"] == "confirmado"
    assert pedido_compra.transicionar(pedido, "recebido")["para"] == "recebido"
    try:
        pedido_compra.transicionar(pedido, "cancelado")
        assert False, "recebido não pode cancelar"
    except ValueError:
        pass
    # pedido parcial mantém aberto
    assert pedido_compra.pode_receber(pedido) is False  # já recebido


def test_cancelar(system_db):
    cot_id, _ = _setup_pedido(system_db)
    pedido = pedido_compra.gerar_pedido(cot_id)["pedidos"][0]
    pedido_compra.transicionar(pedido, "aprovado")
    r = pedido_compra.cancelar(pedido, "não vamos comprar")
    assert r["para"] == "cancelado"
    assert pedido_compra.pode_receber(pedido) is False
    assert pedido_compra.cancelar(pedido)["duplicado"] is True


def test_historico_produto(system_db):
    cot_id, pid = _setup_pedido(system_db)
    pedido_compra.gerar_pedido(cot_id)
    h = pedido_compra.historico_produto(pid)
    assert len(h["precos"]) == 1
    assert h["precos"][0]["fornecedor"] == "F1"
    assert float(h["precos"][0]["preco_unitario"]) == 8.5
    assert len(h["preferenciais"]) == 1


def test_api_pedido(system_db):
    cot_id, _ = _setup_pedido(system_db)
    uid = _usuario("pc_api")
    with system_conn() as conn:
        conn.execute(
            "INSERT INTO usuario_perfis (usuario_id, perfil_id) SELECT %s, id FROM perfis WHERE nome='Administrador'",
            (uid,),
        )
        conn.commit()
    permissao.invalidar(uid)
    client = create_app().test_client()
    h = {"Authorization": f"Bearer {auth_token.criar_token({'id': uid, 'login': 'pc_api'})}"}
    r = client.post(f"/api/cotacoes/{cot_id}/gerar-pedido", headers=h, json={})
    assert r.status_code == 200, r.get_json()
    pedido = r.get_json()["pedidos"][0]
    r = client.post(f"/api/compras/pedidos/{pedido}/status", headers=h, json={"status": "enviado"})
    assert r.status_code == 400  # rascunho→enviado é inválido
    r = client.post(f"/api/compras/pedidos/{pedido}/status", headers=h, json={"status": "aprovado"})
    assert r.status_code == 200
    r = client.post(f"/api/compras/pedidos/{pedido}/status", headers=h, json={"status": "enviado"})
    assert r.status_code == 200
    r = client.post(f"/api/compras/pedidos/{pedido}/status", headers=h, json={"status": "recebido"})
    assert r.status_code == 400  # enviado→recebido direto é inválido (exige confirmado)
    r = client.post(f"/api/compras/pedidos/{pedido}/status", headers=h, json={"status": "confirmado"})
    assert r.status_code == 200
    r = client.post(f"/api/compras/pedidos/{pedido}/cancelar", headers=h, json={"motivo": "teste"})
    assert r.status_code == 200