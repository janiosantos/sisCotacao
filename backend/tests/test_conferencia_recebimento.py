"""Conferência por código/unidade (REC-002)."""
from __future__ import annotations

from catalog_server import auth_token, permissao
from catalog_server.app_factory import create_app
from catalog_server.db import system_conn
from catalog_server.repositories.compras_avancado import solicitacao_repo
from catalog_server.services import cotacao_necessidade, comparacao, pedido_compra, recebimento, conferencia


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


def _setup_rec(system_db, sku: str = "CONF-1") -> tuple[int, int, int, int]:
    solic = _usuario("conf_sol")
    aprov = _usuario("conf_apr")
    with system_conn() as conn:
        pid = int(conn.execute(
            "INSERT INTO produtos_cadastro (nome, ativo, sku, ean, preco, custo_unitario, unidade_venda, fator_conversao)"
            " VALUES (%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id",
            ("Cabo", 1, sku, "7891000000001", 10.0, 5.0, "CX", 100),
        ).fetchone()["id"])
        conn.execute("INSERT INTO fornecedores (nome, whatsapp) VALUES (%s,%s)", ("F1", "1"))
        f1 = int(conn.execute("SELECT lastval()").fetchone()["lastval"])
        conn.execute("INSERT INTO fornecedor_preferencial (produto_id, fornecedor_id, ranking) VALUES (%s,%s,1)", (pid, f1))
        did = int(conn.execute("SELECT id FROM depositos ORDER BY id LIMIT 1").fetchone()["id"])
        # conversão CX→UN (1 CX = 100 UN)
        conn.execute("INSERT INTO unidade_conversao (produto_id, unidade_origem, unidade_destino, fator, unidade_base)"
                     " VALUES (%s,'CX','UN',100,'UN')", (pid,))
        conn.commit()
    sc = solicitacao_repo.create("SOL-CONF", usuario_id=solic)
    solicitacao_repo.add_item(sc, pid, 500, unidade="UN")  # 500 unidades base
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
    rid = recebimento.criar(pedido, did, "NF-CONF")["recebimento_id"]
    return rid, pid, did, pedido


def test_resolver_codigo_sku(system_db):
    _, pid, _, _ = _setup_rec(system_db)
    r = conferencia.resolver_codigo("CONF-1")
    assert r["produto_id"] == pid
    assert r["unidade_base"] == "UN"
    r2 = conferencia.resolver_codigo("7891000000001")
    assert r2["produto_id"] == pid


def test_resolver_desconhecido(system_db):
    _setup_rec(system_db)
    assert conferencia.resolver_codigo("NAO-EXISTE") is None


def test_conferir_por_caixa_converte(system_db):
    rid, pid, _, _ = _setup_rec(system_db)
    # confere 5 caixas (CX) = 500 unidades base
    r = conferencia.conferir_por_codigo(rid, "CONF-1", 5, "CX")
    assert r["quantidade_base"] == 500.0
    assert r["quantidade_esperada"] == 500.0
    assert r["divergencia"] == 0.0
    assert r["status"] == "aceito"


def test_divergencia_de_quantidade(system_db):
    rid, pid, _, _ = _setup_rec(system_db)
    r = conferencia.conferir_por_codigo(rid, "CONF-1", 4, "CX")
    assert r["quantidade_base"] == 400.0
    assert r["divergencia"] == -100.0  # esperado 500, conferido 400


def test_produto_fora_da_lista_rejeita(system_db):
    rid, _, _, _ = _setup_rec(system_db, sku="CONF-2")
    with system_conn() as conn:
        conn.execute(
            "INSERT INTO produtos_cadastro (nome, ativo, sku, ean, preco, unidade_venda)"
            " VALUES (%s,%s,%s,%s,%s,%s)",
            ("Outro", 1, "OUTRO-1", "7891000000999", 1.0, "UN"),
        )
        conn.commit()
    try:
        conferencia.conferir_por_codigo(rid, "OUTRO-1", 1)
        assert False, "produto fora da lista deveria falhar"
    except ValueError as exc:
        assert "não está na lista" in str(exc)


def test_api_scanner(system_db):
    rid, _, _, _ = _setup_rec(system_db)
    uid = _usuario("conf_api")
    with system_conn() as conn:
        conn.execute(
            "INSERT INTO usuario_perfis (usuario_id, perfil_id) SELECT %s, id FROM perfis WHERE nome='Administrador'",
            (uid,),
        )
        conn.commit()
    permissao.invalidar(uid)
    client = create_app().test_client()
    h = {"Authorization": f"Bearer {auth_token.criar_token({'id': uid, 'login': 'conf_api'})}"}
    r = client.post(f"/api/compras/recebimentos/{rid}/itens/scanner", headers=h, json={"codigo": "CONF-1", "quantidade": 5, "unidade": "CX"})
    assert r.status_code == 200, r.get_json()
    assert r.get_json()["conferencia"]["quantidade_base"] == 500.0
    r = client.get("/api/compras/conferencia/resolver?codigo=CONF-1", headers=h)
    assert r.status_code == 200
    r = client.get("/api/compras/conferencia/resolver?codigo=XYZ", headers=h)
    assert r.status_code == 404