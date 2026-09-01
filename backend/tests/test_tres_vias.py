"""Conferência de três vias (REC-003)."""
from __future__ import annotations

from catalog_server import auth_token, permissao
from catalog_server.app_factory import create_app
from catalog_server.db import system_conn
from catalog_server.repositories.compras_avancado import solicitacao_repo
from catalog_server.services import cotacao_necessidade, comparacao, pedido_compra, recebimento, tres_vias


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


def _setup_rec(system_db, tolerancia_qtd: float = 10) -> tuple[int, int, int, int]:
    solic = _usuario("tv_sol")
    aprov = _usuario("tv_apr")
    with system_conn() as conn:
        pid = int(conn.execute(
            "INSERT INTO produtos_cadastro (nome, ativo, sku, preco, custo_unitario, unidade_venda) VALUES (%s,%s,%s,%s,%s,%s) RETURNING id",
            ("P", 1, "TV-1", 10.0, 5.0, "UN"),
        ).fetchone()["id"])
        conn.execute("INSERT INTO fornecedores (nome, whatsapp) VALUES (%s,%s)", ("F1", "1"))
        f1 = int(conn.execute("SELECT lastval()").fetchone()["lastval"])
        conn.execute("INSERT INTO fornecedor_preferencial (produto_id, fornecedor_id, ranking) VALUES (%s,%s,1)", (pid, f1))
        conn.execute(
            "INSERT INTO tolerancias_compra (fornecedor_id, tolerancia_preco_pct, tolerancia_qtd_pct, exige_aprovacao)"
            " VALUES (%s,5,%s,1)", (f1, tolerancia_qtd),
        )
        did = int(conn.execute("SELECT id FROM depositos ORDER BY id LIMIT 1").fetchone()["id"])
        conn.commit()
    sc = solicitacao_repo.create("SOL-TV", usuario_id=solic)
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
    rid = recebimento.criar(pedido, did, "NF-TV")["recebimento_id"]
    return rid, pid, did, pedido


def test_sem_divergencia_aprovado(system_db):
    rid, pid, _, _ = _setup_rec(system_db)
    r = tres_vias.conferir(rid, [{"produto_id": pid, "quantidade": 10, "preco_unitario": 8.0}])
    assert r["status_tres_vias"] == "aprovado"
    assert r["divergencias"] == 0


def test_divergencia_dentro_tolerancia(system_db):
    rid, pid, _, _ = _setup_rec(system_db, tolerancia_qtd=10)
    # 10% a mais na quantidade (dentro da tolerância de 10%)
    r = tres_vias.conferir(rid, [{"produto_id": pid, "quantidade": 11, "preco_unitario": 8.0}])
    assert r["status_tres_vias"] == "aprovado"
    div = tres_vias.divergencias(rid)
    qtd = [d for d in div if d["tipo"] == "quantidade"][0]
    assert qtd["dentro_tolerancia"] is True


def test_divergencia_fora_tolerancia_exige_aprovacao(system_db):
    rid, pid, _, _ = _setup_rec(system_db, tolerancia_qtd=10)
    # 30% a mais na quantidade → divergente
    r = tres_vias.conferir(rid, [{"produto_id": pid, "quantidade": 13, "preco_unitario": 8.0}])
    assert r["status_tres_vias"] == "divergente"
    div = tres_vias.divergencias(rid)
    qtd = [d for d in div if d["tipo"] == "quantidade"][0]
    assert qtd["dentro_tolerancia"] is False
    # finalizar bloqueado até aprovar
    # conferir fisicamente (aceita o que o pedido permite)
    item = recebimento.detalhe(rid)["itens"][0]
    recebimento.conferir_item(rid, item["id"], 10)
    try:
        recebimento.finalizar(rid)
        assert False, "divergência sem aprovação não pode finalizar"
    except ValueError as exc:
        assert "aprovação" in str(exc)
    tres_vias.aprovar(rid, 1)
    res = recebimento.finalizar(rid)
    assert res["pedido_status"] == "recebido"


def test_divergencia_preco(system_db):
    rid, pid, _, _ = _setup_rec(system_db)
    # preço 12 (50% maior) → divergente (tolerância 5%)
    r = tres_vias.conferir(rid, [{"produto_id": pid, "quantidade": 10, "preco_unitario": 12.0}])
    assert r["status_tres_vias"] == "divergente"


def test_item_nf_sem_pedido(system_db):
    rid, _, _, _ = _setup_rec(system_db)
    with system_conn() as conn:
        conn.execute(
            "INSERT INTO produtos_cadastro (nome, ativo, sku, preco, unidade_venda) VALUES (%s,%s,%s,%s,%s)",
            ("Extra", 1, "EXTRA-1", 1.0, "UN"),
        )
        conn.commit()
    with system_conn() as conn:
        eid = int(conn.execute("SELECT id FROM produtos_cadastro WHERE sku='EXTRA-1'").fetchone()["id"])
    r = tres_vias.conferir(rid, [{"produto_id": eid, "quantidade": 5, "preco_unitario": 1.0}])
    assert r["status_tres_vias"] == "divergente"


def test_rejeitar(system_db):
    rid, pid, _, _ = _setup_rec(system_db)
    tres_vias.conferir(rid, [{"produto_id": pid, "quantidade": 13, "preco_unitario": 8.0}])
    r = tres_vias.rejeitar(rid, "nota errada")
    assert r["status_tres_vias"] == "rejeitado"
    try:
        tres_vias.aprovar(rid, 1)
        assert False, "rejeitado não pode aprovar"
    except ValueError:
        pass


def test_api_tres_vias(system_db):
    rid, pid, _, _ = _setup_rec(system_db)
    uid = _usuario("tv_api")
    with system_conn() as conn:
        conn.execute(
            "INSERT INTO usuario_perfis (usuario_id, perfil_id) SELECT %s, id FROM perfis WHERE nome='Administrador'",
            (uid,),
        )
        conn.commit()
    permissao.invalidar(uid)
    client = create_app().test_client()
    h = {"Authorization": f"Bearer {auth_token.criar_token({'id': uid, 'login': 'tv_api'})}"}
    r = client.post(f"/api/compras/recebimentos/{rid}/tres-vias", headers=h,
                    json={"itens_nf": [{"produto_id": pid, "quantidade": 10, "preco_unitario": 8.0}]})
    assert r.status_code == 200, r.get_json()
    assert r.get_json()["status_tres_vias"] == "aprovado"
    assert client.get(f"/api/compras/recebimentos/{rid}/divergencias", headers=h).status_code == 200