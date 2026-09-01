"""Motor de reposição (COM-004): necessidade com todos os componentes, sem duplicar compra."""
from __future__ import annotations

from catalog_server import auth_token, permissao
from catalog_server.app_factory import create_app
from catalog_server.db import system_conn
from catalog_server.repositories import estoque_repo
from catalog_server.services import motor_reposicao as motor


def _setup(system_db) -> tuple[int, int, int]:
    with system_conn() as conn:
        conn.execute("INSERT INTO produtos_cadastro (nome, ativo, sku, preco, custo_unitario, unidade_venda) VALUES (%s,%s,%s,%s,%s,%s)", ("P", 1, "M-1", 10.0, 5.0, "UN"))
        pid = int(conn.execute("SELECT lastval()").fetchone()["lastval"])
        cid = int(conn.execute("INSERT INTO clientes (nome, doc, tipo_pessoa) VALUES (%s,%s,%s) RETURNING id", ("C", "1", "F")).fetchone()["id"])
        did = int(conn.execute("SELECT id FROM depositos ORDER BY id LIMIT 1").fetchone()["id"])
        # 6 meses de vendas: 30 un/mês
        for i in range(1, 7):
            oid = int(conn.execute(
                "INSERT INTO orcamentos (cliente_id, numero, status, criado_em) VALUES (%s,%s,%s,%s) RETURNING id",
                (cid, f"O-{i}", "finalizado", f"2026-0{i}-10 10:00:00"),
            ).fetchone()["id"])
            conn.execute(
                "INSERT INTO orcamento_itens (orcamento_id, produto_id, nome, quantidade, preco_unitario, subtotal)"
                " VALUES (%s,%s,%s,%s,%s,%s)", (oid, pid, "P", 30, 10.0, 300.0),
            )
        conn.commit()
        return pid, did, cid


def test_necessidade_sem_estoque(system_db):
    pid, did, _ = _setup(system_db)
    with system_conn() as conn:
        conn.execute("INSERT INTO fornecedores (nome, whatsapp, prazo_entrega_dias) VALUES (%s,%s,%s)", ("Fornecedor", "55", 15))
        fid = int(conn.execute("SELECT lastval()").fetchone()["lastval"])
        conn.execute("INSERT INTO fornecedor_preferencial (produto_id, fornecedor_id, ranking, ultimo_preco) VALUES (%s,%s,1,%s)", (pid, fid, 8.0))
        conn.commit()
    r = motor.calcular(produto_id=pid)
    s = r["sugestoes"][0]
    # sem estoque, alvo 0 (sem parâmetro) → necessidade = demanda no lead time (30×15/30 = 15)
    assert s["sugestao"] > 0
    assert s["demanda_lead_time"] == 15.0
    assert s["fornecedor_nome"] == "Fornecedor"
    assert s["ultimo_preco"] == 8.0
    assert s["disponivel_projetado"] == 0.0


def test_transito_evita_duplicar(system_db):
    pid, did, _ = _setup(system_db)
    with system_conn() as conn:
        conn.execute("INSERT INTO fornecedores (nome, whatsapp, prazo_entrega_dias) VALUES (%s,%s,%s)", ("F2", "55", 15))
        fid = int(conn.execute("SELECT lastval()").fetchone()["lastval"])
        conn.execute("INSERT INTO fornecedor_preferencial (produto_id, fornecedor_id, ranking, ultimo_preco) VALUES (%s,%s,1,8.0)", (pid, fid))
        # pedido em trânsito (enviado) cobrindo 30 un
        conn.execute("INSERT INTO cotacoes (numero, status) VALUES (%s,%s)", ("COT-1", "fechada"))
        cid_cot = int(conn.execute("SELECT lastval()").fetchone()["lastval"])
        conn.execute("INSERT INTO cotacao_itens (cotacao_id, produto_id, quantidade) VALUES (%s,%s,30)", (cid_cot, pid))
        citem = int(conn.execute("SELECT lastval()").fetchone()["lastval"])
        conn.execute("INSERT INTO pedidos_compra (numero, cotacao_id, fornecedor_id, status) VALUES (%s,%s,%s,%s)", ("PC-1", cid_cot, fid, "enviado"))
        pidc = int(conn.execute("SELECT lastval()").fetchone()["lastval"])
        conn.execute("INSERT INTO pedido_itens (cotacao_id, cotacao_item_id, pedido_id, fornecedor_id, preco_unitario, quantidade) VALUES (%s,%s,%s,%s,8.0,30)", (cid_cot, citem, pidc, fid))
        conn.commit()
    r = motor.calcular(produto_id=pid)
    s = r["sugestoes"][0]
    assert s["transito"] == 30.0
    # trânsito (30) >= demanda_lead (15) → não duplica
    assert s["sugestao"] == 0.0


def test_ruptura_provavel(system_db):
    pid, did, _ = _setup(system_db)
    estoque_repo.movimentar_fato(did, pid, "entrada", 60, origem_tipo="teste")
    r = motor.calcular(produto_id=pid)
    s = r["sugestoes"][0]
    assert s["disponivel"] == 60.0
    # 60 / (30/30) = 60 dias
    assert s["ruptura_provavel"] is not None


def test_lote_multiplo_arredonda(system_db):
    pid, did, _ = _setup(system_db)
    with system_conn() as conn:
        conn.execute(
            "INSERT INTO estoque_parametro (produto_id, deposito_id, politica, minimo, maximo, lote_multiplo, lead_time_dias)"
            " VALUES (%s,%s,'manual',10,50,5,15)",
            (pid, did),
        )
        conn.commit()
    r = motor.calcular(produto_id=pid, deposito_id=did)
    s = r["sugestoes"][0]
    # alvo=50, demanda_lead=15, disp=0 → 65 → múltiplo de 5 = 65
    assert s["estoque_alvo"] == 50.0
    assert s["sugestao"] % 5 == 0


def test_sob_encomenda_nao_vira_estoque(system_db):
    pid, did, _ = _setup(system_db)
    with system_conn() as conn:
        conn.execute(
            "INSERT INTO estoque_parametro (produto_id, deposito_id, politica, minimo, maximo, lead_time_dias)"
            " VALUES (%s,%s,'sob_encomenda',0,100,15)",
            (pid, did),
        )
        conn.commit()
    r = motor.calcular(produto_id=pid, deposito_id=did)
    s = r["sugestoes"][0]
    assert s["sob_encomenda"] is True
    assert s["sugestao"] == 0.0


def test_api_reposicao(system_db):
    pid, did, _ = _setup(system_db)
    uid = _usuario("motor")
    with system_conn() as conn:
        conn.execute(
            "INSERT INTO usuario_perfis (usuario_id, perfil_id) SELECT %s, id FROM perfis WHERE nome='Administrador'",
            (uid,),
        )
        conn.commit()
    permissao.invalidar(uid)
    client = create_app().test_client()
    h = {"Authorization": f"Bearer {auth_token.criar_token({'id': uid, 'login': 'motor'})}"}
    r = client.get(f"/api/estoque/reposicao?produto_id={pid}&deposito_id={did}", headers=h)
    assert r.status_code == 200, r.get_json()
    assert r.get_json()["sugestoes"][0]["produto_id"] == pid


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