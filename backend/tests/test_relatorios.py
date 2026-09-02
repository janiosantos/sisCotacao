"""Relatórios e indicadores (BI-001..007)."""
from __future__ import annotations

from catalog_server import auth_token, permissao
from catalog_server.app_factory import create_app
from catalog_server.db import system_conn
from catalog_server.repositories import estoque_repo
from catalog_server.services import relatorios


def _setup(system_db) -> int:
    with system_conn() as conn:
        cid = int(conn.execute("INSERT INTO clientes (nome, doc, tipo_pessoa) VALUES (%s,%s,%s) RETURNING id", ("C", "1", "F")).fetchone()["id"])
        pid = int(conn.execute(
            "INSERT INTO produtos_cadastro (nome, ativo, sku, preco, custo_unitario) VALUES (%s,%s,%s,%s,%s) RETURNING id",
            ("P", 1, "BI-1", 10.0, 5.0),
        ).fetchone()["id"])
        oid = int(conn.execute(
            "INSERT INTO orcamentos (cliente_id, numero, status, cliente, total, subtotal, criado_em)"
            " VALUES (%s,%s,'finalizado',%s,200.0,200.0,'2026-08-10 10:00:00') RETURNING id",
            (cid, "BI-O1", "Cliente"),
        ).fetchone()["id"])
        conn.execute(
            "INSERT INTO orcamento_itens (orcamento_id, produto_id, nome, quantidade, preco_unitario, subtotal)"
            " VALUES (%s,%s,%s,20,10.0,200.0)", (oid, pid, "P"),
        )
        did = int(conn.execute("SELECT id FROM depositos ORDER BY id LIMIT 1").fetchone()["id"])
        conn.commit()
    estoque_repo.movimentar_fato(did, pid, "entrada", 20, custo_unitario=5.0, origem_tipo="teste")
    estoque_repo.movimentar_fato(did, pid, "saida", 20, custo_unitario=5.0, origem_tipo="venda", origem_id=oid)
    with system_conn() as conn:
        conn.execute("UPDATE estoque_movimento SET criado_em='2026-08-15 10:00:00' WHERE produto_id=%s", (pid,))
        conn.execute(
            "INSERT INTO contas_receber (cliente, cliente_id, descricao, valor, saldo, data_vencimento, data_emissao, status)"
            " VALUES (%s,%s,%s,50,50,%s,%s,'aberto')",
            ("C", cid, "Venda", "2026-06-01", "2026-05-01"),
        )
        conn.commit()
    return oid


def test_dashboard_executivo(system_db):
    _setup(system_db)
    d = relatorios.dashboard_executivo("2026-08-01", "2026-08-31")
    k = d["kpis"]
    assert k["receita_liquida"] == 200.0
    assert k["cmv"] == 100.0  # 20 × 5
    assert k["margem_pct"] == 50.0
    assert k["pedidos"] == 1
    assert k["ticket_medio"] == 200.0
    assert k["inadimplencia"] == 50.0


def test_vendas_agrupadas(system_db):
    oid = _setup(system_db)
    r = relatorios.vendas("2026-08-01", "2026-08-31", agrupamento="produto")
    assert r["cmv"] == 100.0
    assert len(r["itens"]) == 1
    assert r["itens"][0]["receita_liquida"] == 200.0
    assert r["cancelados"]["pedidos"] == 0


def test_compras(system_db):
    _setup(system_db)
    c = relatorios.compras("2026-01-01", "2026-12-31")
    assert "pedidos" in c
    assert "lead_time_medio_dias" in c


def test_estoque(system_db):
    _setup(system_db)
    e = relatorios.estoque()
    # 20 entradas - 20 saídas = 0 → sem itens com saldo
    assert e["totais"]["produtos"] == 0


def test_financeiro_dre(system_db):
    _setup(system_db)
    f = relatorios.financeiro("2026-08-01", "2026-08-31")
    assert f["dre"]["receita_liquida"] == 200.0
    assert f["dre"]["cmv"] == 100.0
    assert f["dre"]["lucro_bruto"] == 100.0
    assert f["aging"]["vencido"] == 50.0


def test_central(system_db):
    c = relatorios.central()
    assert any(r["key"] == "dashboard" for r in c["relatorios"])
    assert any(r["key"] == "financeiro" for r in c["relatorios"])


def test_admin_recebe_permissao_da_central_de_relatorios(system_db):
    uid = _usuario("bi_rbac")
    with system_conn() as conn:
        conn.execute(
            "INSERT INTO usuario_perfis (usuario_id, perfil_id) "
            "SELECT %s, id FROM perfis WHERE nome='Administrador'",
            (uid,),
        )
        conn.commit()
    permissao.invalidar(uid)
    assert "relatorios.visualizar" in api_permissoes_efetivas(uid)


def test_api_relatorios(system_db):
    _setup(system_db)
    uid = _usuario("bi_api")
    with system_conn() as conn:
        conn.execute(
            "INSERT INTO usuario_perfis (usuario_id, perfil_id) SELECT %s, id FROM perfis WHERE nome='Administrador'",
            (uid,),
        )
        conn.commit()
    permissao.invalidar(uid)
    client = create_app().test_client()
    h = {"Authorization": f"Bearer {auth_token.criar_token({'id': uid, 'login': 'bi_api'})}"}
    assert client.get("/api/relatorios/dashboard?data_inicio=2026-08-01&data_fim=2026-08-31", headers=h).status_code == 200
    assert client.get("/api/relatorios/vendas", headers=h).status_code == 200
    assert client.get("/api/relatorios/compras", headers=h).status_code == 200
    assert client.get("/api/relatorios/estoque", headers=h).status_code == 200
    assert client.get("/api/relatorios/financeiro", headers=h).status_code == 200
    assert client.get("/api/relatorios/central", headers=h).status_code == 200


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


def api_permissoes_efetivas(usuario_id: int) -> list[str]:
    from catalog_server.blueprints.api_permissoes import permissoes_efetivas

    return permissoes_efetivas(usuario_id)
