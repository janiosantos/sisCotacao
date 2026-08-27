"""Pedidos de compra (v2.21.0): recebimento e consulta no pipeline Compras.

Cobre:
- listar pedidos de compra com status e total;
- receber pedido: entrada de estoque + conta a pagar + status 'recebido';
- receber pedido já recebido bloqueia (400).
"""
from __future__ import annotations

from catalog_server import auth_token
from catalog_server.db import system_conn
from catalog_server.app_factory import create_app


def _usuario(login: str) -> int:
    from werkzeug.security import generate_password_hash

    with system_conn() as conn:
        cur = conn.execute(
            "INSERT INTO usuarios (nome, login, senha_hash, desconto_limite_pct)"
            " VALUES (%s,%s,%s,5)",
            ("Comprador", login, generate_password_hash("x123")),
        )
        uid = int(cur.lastrowid)
        conn.commit()
    return uid


def _perfil_id(nome: str) -> int:
    with system_conn() as conn:
        return int(conn.execute(
            "SELECT id FROM perfis WHERE nome=%s", (nome,)
        ).fetchone()["id"])


def _admin_client(system_db):
    uid = _usuario("admcompras")
    from catalog_server import permissao

    with system_conn() as conn:
        conn.execute(
            "INSERT INTO usuario_perfis (usuario_id, perfil_id) VALUES (%s,%s) ON CONFLICT DO NOTHING",
            (uid, _perfil_id("Administrador")),
        )
        conn.commit()
    permissao.invalidar(uid)
    c = create_app().test_client()
    h = {"Authorization": f"Bearer {auth_token.criar_token({'id': uid, 'login': 'admcompras'})}"}
    return c, h


def _setup_pedido(system_db, c, h) -> tuple[int, int]:
    """Cria produto/variante, fornecedor e cotação com proposta → gera pedido."""
    from catalog_server.repositories import supplier_repo

    with system_conn() as conn:
        conn.execute(
            "INSERT INTO produtos_cadastro (nome, ativo, sku, ean, preco, unidade_venda, fator_conversao)"
            " VALUES (%s,%s,%s,%s,%s,%s,%s)",
            ('Argamassa', 1, 'ARG-20', '7891000000002', 10, 'SC', 20),
        )
        pid = int(conn.execute("SELECT lastval()").fetchone()["lastval"])
        conn.commit()

    fid = supplier_repo.create({"nome": "Argamassas BR", "whatsapp": "5511998887777"})
    r = c.post("/api/compras/cotacoes", headers=h, json={
        "apelido": "Cotação Argamassa",
        "comprador": "Loja",
        "itens": [{"produto_id": pid, "quantidade": 40}],
        "fornecedores": [{"fornecedor_id": fid}],
    })
    assert r.status_code == 200, r.get_json()
    cid = r.get_json()["id"]
    token = r.get_json()["invites"][0]["token"]

    # resposta do portal com preço
    pr = c.post(f"/api/fornecedor/{token}/proposta", json={
        "precos": [{
            "cotacao_item_id": 1,
            "preco_unitario": 12.5,
            "disponibilidade_estoque": 1,
            "unidade_compra": "SC",
            "fator_conversao": 20,
            "marca_ofertada": "Argamassas BR",
        }],
        "condicao_pagamento": "30 dias",
        "condicao_pagamento_dias": 30,
    })
    assert pr.status_code == 200, pr.get_json()

    # gera pedido
    rp = c.post(f"/api/compras/cotacoes/{cid}/pedidos", headers=h, json={"logica": "fracionado"})
    assert rp.status_code == 200, rp.get_json()
    pedidos = rp.get_json()["pedidos"]
    assert len(pedidos) == 1
    return pedidos[0]["id"], fid


def test_listar_pedidos(system_db):
    c, h = _admin_client(system_db)
    _setup_pedido(system_db, c, h)
    r = c.get("/api/compras/pedidos", headers=h)
    assert r.status_code == 200
    assert len(r.get_json()) == 1
    ped = r.get_json()[0]
    assert ped["status"] == "enviado"
    assert ped["total"] > 0


def test_receber_pedido_atualiza_status(system_db):
    c, h = _admin_client(system_db)
    pid, _ = _setup_pedido(system_db, c, h)
    r = c.post(f"/api/compras/pedidos/{pid}/receber", headers=h, json={})
    assert r.status_code == 200, r.get_json()
    body = r.get_json()
    assert body["ok"] is True
    with system_conn() as conn:
        st = conn.execute("SELECT status FROM pedidos_compra WHERE id=%s", (pid,)).fetchone()
    assert st["status"] == "recebido"
    # estoque recebeu entrada
    with system_conn() as conn:
        qtd = conn.execute(
            "SELECT COALESCE(SUM(quantidade),0) FROM estoque_movimento WHERE documento=%s",
            ("0001",),
        ).fetchone()[0]
    assert qtd > 0


def test_receber_pedido_ja_recebido_bloqueia(system_db):
    c, h = _admin_client(system_db)
    pid, _ = _setup_pedido(system_db, c, h)
    assert c.post(f"/api/compras/pedidos/{pid}/receber", headers=h, json={}).status_code == 200
    r2 = c.post(f"/api/compras/pedidos/{pid}/receber", headers=h, json={})
    assert r2.status_code == 400


def test_solicitacao_detalhe_com_itens(system_db):
    c, h = _admin_client(system_db)
    with system_conn() as conn:
        conn.execute(
            "INSERT INTO produtos_cadastro (nome, ativo, sku, ean, preco, unidade_venda)"
            " VALUES (%s,%s,%s,%s,%s,%s)",
            ('Cimento', 1, 'CIM-50', '7891000000003', 32, 'SC'),
        )
        pid = int(conn.execute("SELECT lastval()").fetchone()["lastval"])
        conn.commit()
    r = c.post("/api/solicitacoes-compra", headers=h, json={"codigo": "SOL-001", "descricao": "Repor estoque"})
    sc_id = r.get_json()["id"]
    c.post(f"/api/solicitacoes-compra/{sc_id}/itens", headers=h, json={"variante_id": pid, "quantidade": 10})

    d = c.get(f"/api/solicitacoes-compra/{sc_id}", headers=h)
    assert d.status_code == 200
    body = d.get_json()
    assert body["codigo"] == "SOL-001"
    assert len(body["itens"]) == 1
    assert body["itens"][0]["produto_nome"] == "Cimento"


def test_editar_quantidade_item_cotacao_compras(system_db):
    """Edição de quantidade de item numa cotação criada pelo fluxo Compras
    (tela 'aguardando respostas') usa o PATCH de itens da cotação."""
    c, h = _admin_client(system_db)
    with system_conn() as conn:
        conn.execute(
            "INSERT INTO produtos_cadastro (nome, ativo, sku, ean, preco, unidade_venda)"
            " VALUES (%s,%s,%s,%s,%s,%s)",
            ('Cimento', 1, 'CIM-50', '7891000000003', 32, 'SC'),
        )
        pid = int(conn.execute("SELECT lastval()").fetchone()["lastval"])
        conn.commit()
    from catalog_server.repositories import supplier_repo

    fid = supplier_repo.create({"nome": "Cimento Norte"})
    r = c.post("/api/compras/cotacoes", headers=h, json={
        "apelido": "Cotação Cimento",
        "comprador": "Loja",
        "itens": [{"produto_id": pid, "quantidade": 10}],
        "fornecedores": [{"fornecedor_id": fid}],
    })
    assert r.status_code == 200, r.get_json()
    cid = r.get_json()["id"]

    up = c.patch(f"/api/cotacoes/{cid}/itens/1", headers=h, json={"quantidade": 25})
    assert up.status_code == 200, up.get_json()
    with system_conn() as conn:
        qtd = conn.execute("SELECT quantidade FROM cotacao_itens WHERE id=1").fetchone()["quantidade"]
    assert float(qtd) == 25