"""ABC histórica (COM-001): cálculo reproduzível por período/critério, versionado, sem cancelamentos."""
from __future__ import annotations

from catalog_server import auth_token, permissao
from catalog_server.app_factory import create_app
from catalog_server.db import system_conn
from catalog_server.services import abc_historica as abc


def _produto(conn, nome: str, sku: str) -> int:
    return int(conn.execute(
        "INSERT INTO produtos_cadastro (nome, ativo, sku, preco, custo_unitario) VALUES (%s,%s,%s,%s,%s) RETURNING id",
        (nome, 1, sku, 10.0, 5.0),
    ).fetchone()["id"])


def _venda(conn, cliente_id: int, numero: str, status: str, criado_em: str, itens: list) -> int:
    oid = int(conn.execute(
        "INSERT INTO orcamentos (cliente_id, numero, status, criado_em) VALUES (%s,%s,%s,%s) RETURNING id",
        (cliente_id, numero, status, criado_em),
    ).fetchone()["id"])
    for pid, qtd, preco in itens:
        conn.execute(
            "INSERT INTO orcamento_itens (orcamento_id, produto_id, nome, quantidade, preco_unitario, subtotal)"
            " VALUES (%s,%s,%s,%s,%s,%s)",
            (oid, pid, "X", qtd, preco, qtd * preco),
        )
    return oid


def _setup(system_db) -> tuple[int, int, int, int]:
    with system_conn() as conn:
        cid = int(conn.execute("INSERT INTO clientes (nome, doc, tipo_pessoa) VALUES (%s,%s,%s) RETURNING id", ("C", "1", "F")).fetchone()["id"])
        p1 = _produto(conn, "Alto", "P-1")
        p2 = _produto(conn, "Médio", "P-2")
        p3 = _produto(conn, "Baixo", "P-3")
        p4 = _produto(conn, "Sem venda", "P-4")
        did = int(conn.execute("SELECT id FROM depositos ORDER BY id LIMIT 1").fetchone()["id"])
        # vendas finalizadas
        _venda(conn, cid, "O-1", "finalizado", "2026-08-01 10:00:00", [(p1, 100, 10.0)])
        _venda(conn, cid, "O-2", "finalizado", "2026-08-02 10:00:00", [(p1, 50, 10.0), (p2, 30, 10.0)])
        _venda(conn, cid, "O-3", "finalizado", "2026-08-03 10:00:00", [(p3, 5, 10.0)])
        # cancelada — não deve contar
        _venda(conn, cid, "O-4", "cancelado", "2026-08-04 10:00:00", [(p1, 999, 10.0)])
        # fora do período
        _venda(conn, cid, "O-5", "finalizado", "2026-01-01 10:00:00", [(p1, 999, 10.0)])
        conn.commit()
        return p1, p2, p3, p4


def test_calcular_quantidade_exclui_cancelado(system_db):
    p1, p2, p3, _ = _setup(system_db)
    r = abc.calcular("quantidade", "2026-08-01", "2026-08-31")
    by_p = {i["produto_id"]: i for i in r["itens"]} if r.get("itens") else {}
    # p1 = 150, p2 = 30, p3 = 5 (o cancelado e o de janeiro NÃO entram)
    assert float(by_p[p1]["valor"]) == 150.0
    assert float(by_p[p2]["valor"]) == 30.0
    assert float(by_p[p3]["valor"]) == 5.0
    assert r["total"] == 185.0


def test_calcular_receita_e_margem(system_db):
    p1, _, _, _ = _setup(system_db)
    r = abc.calcular("receita", "2026-08-01", "2026-08-31")
    by_p = {i["produto_id"]: i for i in r["itens"]}
    assert float(by_p[p1]["valor"]) == 1500.0
    r2 = abc.calcular("margem", "2026-08-01", "2026-08-31")
    by_p2 = {i["produto_id"]: i for i in r2["itens"]}
    # sem movimento de saída registrado, margem = receita - 0
    assert float(by_p2[p1]["valor"]) == 1500.0


def test_classificacao_acumulada(system_db):
    p1, p2, p3, _ = _setup(system_db)
    r = abc.calcular("quantidade", "2026-08-01", "2026-08-31")
    by_p = {i["produto_id"]: i for i in r["itens"]}
    # p1 = 150/185 = 81% -> A? Não — 81% > 70% -> B. p1+p2 = 97% -> B/C.
    assert by_p[p1]["classe"] == "B"  # 81.08%
    assert by_p[p2]["classe"] == "C"  # após 97%
    assert by_p[p3]["classe"] == "C"
    assert r["resumo"]["A"]["produtos"] == 0
    assert r["resumo"]["B"]["produtos"] >= 1


def test_sem_venda_nao_entra_e_aparece_separado(system_db):
    _, _, _, p4 = _setup(system_db)
    r = abc.calcular("quantidade", "2026-08-01", "2026-08-31")
    ids = {i["produto_id"] for i in r["itens"]}
    assert p4 not in ids  # sem venda fica fora da curva
    assert r["sem_venda"] == 0


def test_validacoes(system_db):
    p1, _, _, _ = _setup(system_db)
    try:
        abc.calcular("x", "2026-08-01", "2026-08-31")
        assert False
    except ValueError:
        pass
    try:
        abc.calcular("quantidade", "2026-08-31", "2026-08-01")
        assert False
    except ValueError:
        pass


def test_aplicar_marca_abc_origem(system_db):
    p1, _, _, _ = _setup(system_db)
    r = abc.calcular("quantidade", "2026-08-01", "2026-08-31")
    res = abc.aplicar(r["id"])
    assert res["aplicados"] >= 1
    with system_conn() as conn:
        row = conn.execute("SELECT classe_abc, abc_origem FROM produtos_cadastro WHERE id=%s", (p1,)).fetchone()
    assert row["abc_origem"] == "historico"
    assert row["classe_abc"] in ("A", "B", "C")


def test_listar_e_detalhe(system_db):
    p1, _, _, _ = _setup(system_db)
    r = abc.calcular("quantidade", "2026-08-01", "2026-08-31")
    lst = abc.listar()
    assert any(c["id"] == r["id"] for c in lst)
    det = abc.detalhe(r["id"])
    assert det is not None
    assert len(det["itens"]) == len(r["itens"])


def test_api_abc_fluxo(system_db):
    p1, _, _, _ = _setup(system_db)
    uid = _usuario("abcr")
    with system_conn() as conn:
        conn.execute(
            "INSERT INTO usuario_perfis (usuario_id, perfil_id) SELECT %s, id FROM perfis WHERE nome='Administrador'",
            (uid,),
        )
        conn.commit()
    permissao.invalidar(uid)
    client = create_app().test_client()
    h = {"Authorization": f"Bearer {auth_token.criar_token({'id': uid, 'login': 'abcr'})}"}
    r = client.post("/api/estoque/abc/calcular", headers=h, json={"criterio": "receita", "data_inicio": "2026-08-01", "data_fim": "2026-08-31"})
    assert r.status_code == 200, r.get_json()
    calc_id = r.get_json()["calculo"]["id"]
    assert client.get("/api/estoque/abc", headers=h).status_code == 200
    assert client.get(f"/api/estoque/abc/{calc_id}", headers=h).status_code == 200
    r = client.post(f"/api/estoque/abc/{calc_id}/aplicar", headers=h)
    assert r.status_code == 200


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