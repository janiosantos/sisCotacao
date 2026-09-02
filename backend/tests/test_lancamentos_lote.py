"""Lançamentos parcelados, recorrentes e com origem (v2.25.0).

Cobre (modelo TOTVS/desdobramento):
- parcelamento por condição de pagamento (30/60/90 → valores por percentual);
- parcelamento manual (nº parcelas + intervalo);
- recorrência mensal antecipada;
- preview não grava;
- exclusão de grupo (somente parcelas em aberto);
- recebimento de pedido de compra parcelado pela condição + origem vinculada;
- venda a prazo com grupo/parcela/origem.
"""
from __future__ import annotations

from datetime import date, timedelta

from catalog_server import auth_token
from catalog_server.db import system_conn
from catalog_server.app_factory import create_app


def _usuario(login: str) -> int:
    from werkzeug.security import generate_password_hash

    with system_conn() as conn:
        cur = conn.execute(
            "INSERT INTO usuarios (nome, login, senha_hash, desconto_limite_pct)"
            " VALUES (%s,%s,%s,5)",
            ("Financeiro", login, generate_password_hash("x123")),
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
    uid = _usuario("admlote")
    from catalog_server import permissao

    with system_conn() as conn:
        conn.execute(
            "INSERT INTO usuario_perfis (usuario_id, perfil_id) VALUES (%s,%s) ON CONFLICT DO NOTHING",
            (uid, _perfil_id("Administrador")),
        )
        conn.commit()
    permissao.invalidar(uid)
    c = create_app().test_client()
    h = {"Authorization": f"Bearer {auth_token.criar_token({'id': uid, 'login': 'admlote'})}"}
    return c, h


def _condicao(parcelas: list[tuple[int, float]]) -> int:
    with system_conn() as conn:
        cur = conn.execute(
            "INSERT INTO condicoes_pagamento (nome, descricao, ativo) VALUES ('Teste', '', 1)"
        )
        cid = int(cur.lastrowid)
        for i, (dias, pct) in enumerate(parcelas, start=1):
            conn.execute(
                "INSERT INTO condicao_parcelas (condicao_id, sequencia, dias, percentual) VALUES (%s,%s,%s,%s)",
                (cid, i, dias, pct),
            )
        conn.commit()
    return cid


def _condicao_30_60_90() -> int:
    return _condicao([(30, 33.33), (60, 33.33), (90, 33.34)])


def _aprovar_credito(client, header, cliente_id: int) -> None:
    r = client.post(f"/api/clientes/{cliente_id}/credito/aprovar", headers=header, json={
        "limite_aprovado": 9000,
        "prazo_maximo_dias": 120,
        "vigencia_inicio": date.today().isoformat(),
        "vigencia_fim": (date.today() + timedelta(days=365)).isoformat(),
        "motivo": "Aprovado para teste",
    })
    assert r.status_code == 200, r.get_json()


def test_parcelamento_por_condicao(system_db):
    c, h = _admin_client(system_db)
    cond = _condicao_30_60_90()
    r = c.post("/api/financeiro/pagar/lote", headers=h, json={
        "fornecedor": "Fornecedor Nota",
        "descricao": "Nota 1234",
        "documento": "NF-1234",
        "valor": 3000.0,
        "data_emissao": "2026-08-24",
        "modo": "condicao",
        "condicao_pagamento_id": cond,
    })
    assert r.status_code == 201, r.get_json()
    body = r.get_json()
    assert body["n_parcelas"] == 3
    with system_conn() as conn:
        contas = conn.execute(
            "SELECT * FROM contas_pagar WHERE grupo_id=%s ORDER BY parcela",
            (body["grupo_id"],),
        ).fetchall()
    assert len(contas) == 3
    assert [x["parcela"] for x in contas] == [1, 2, 3]
    soma = round(sum(float(x["valor"]) for x in contas), 2)
    assert soma == 3000.0
    assert contas[0]["origem_tipo"] == "manual"
    assert all(x["documento"] == "NF-1234" for x in contas)
    # vencimentos: emissão + 30/60/90
    assert contas[0]["data_vencimento"] == "2026-09-23"
    assert contas[2]["data_vencimento"] == "2026-11-22"


def test_parcelamento_manual(system_db):
    c, h = _admin_client(system_db)
    r = c.post("/api/financeiro/pagar/lote", headers=h, json={
        "fornecedor": "Fornecedor Manual",
        "descricao": "Compra equipamento",
        "valor": 1200.0,
        "data_emissao": "2026-08-24",
        "modo": "manual",
        "n_parcelas": 4,
        "intervalo_dias": 15,
    })
    assert r.status_code == 201, r.get_json()
    with system_conn() as conn:
        contas = conn.execute(
            "SELECT * FROM contas_pagar WHERE grupo_id=%s ORDER BY parcela",
            (r.get_json()["grupo_id"],),
        ).fetchall()
    assert len(contas) == 4
    assert all(float(x["valor"]) == 300.0 for x in contas)
    # 4ª parcela = emissão (24/08) + 45 dias
    assert contas[3]["data_vencimento"] == "2026-10-08"


def test_recorrencia_mensal(system_db):
    c, h = _admin_client(system_db)
    r = c.post("/api/financeiro/pagar/lote", headers=h, json={
        "fornecedor": "Imobiliária",
        "descricao": "Aluguel do galpão",
        "valor": 2500.0,
        "data_emissao": "2026-09-10",
        "modo": "recorrente",
        "recorrencia": "1",
        "frequencia": "mensal",
        "n_ocorrencias": 6,
        "dia": 10,
    })
    assert r.status_code == 201, r.get_json()
    with system_conn() as conn:
        contas = conn.execute(
            "SELECT * FROM contas_pagar WHERE grupo_id=%s ORDER BY parcela",
            (r.get_json()["grupo_id"],),
        ).fetchall()
    assert len(contas) == 6
    assert all(float(x["valor"]) == 2500.0 for x in contas)
    assert all(x["recorrencia"] == "mensal" for x in contas)
    # 6 meses a partir de 10/09
    assert contas[5]["data_vencimento"] == "2027-02-10"


def test_preview_nao_grava(system_db):
    c, h = _admin_client(system_db)
    cond = _condicao_30_60_90()
    r = c.post("/api/financeiro/lote/preview", headers=h, json={
        "modo": "condicao",
        "valor": 3000.0,
        "data_base": "2026-08-24",
        "condicao_pagamento_id": cond,
    })
    assert r.status_code == 200
    body = r.get_json()
    assert body["n"] == 3
    assert body["total"] == 3000.0
    with system_conn() as conn:
        n = conn.execute("SELECT COUNT(*) FROM contas_pagar").fetchone()[0]
    assert n == 0  # preview não grava


def test_excluir_grupo_so_abertas(system_db):
    c, h = _admin_client(system_db)
    r = c.post("/api/financeiro/pagar/lote", headers=h, json={
        "fornecedor": "Fornecedor Grupo",
        "descricao": "Compra",
        "valor": 900.0,
        "data_emissao": "2026-08-24",
        "modo": "manual",
        "n_parcelas": 3,
        "intervalo_dias": 30,
    })
    grupo = r.get_json()["grupo_id"]
    with system_conn() as conn:
        primeira = conn.execute(
            "SELECT id FROM contas_pagar WHERE grupo_id=%s AND parcela=1",
            (grupo,),
        ).fetchone()["id"]
    # paga a primeira parcela
    c.post(f"/api/financeiro/pagar/{primeira}/pagar", headers=h, json={"valor": 300.0})
    # exclui o grupo
    r2 = c.delete(f"/api/financeiro/lote/pagar/{grupo}", headers=h)
    assert r2.status_code == 200
    assert r2.get_json()["excluidas"] == 2  # só as abertas
    with system_conn() as conn:
        restantes = conn.execute(
            "SELECT COUNT(*) FROM contas_pagar WHERE grupo_id=%s",
            (grupo,),
        ).fetchone()[0]
    assert restantes == 1  # a paga permanece


def test_receber_pedido_parcelado_com_origem(system_db):
    c, h = _admin_client(system_db)
    cond = _condicao_30_60_90()
    from catalog_server.repositories import supplier_repo

    fid = supplier_repo.create({"nome": "Fornecedor Pedido"})
    with system_conn() as conn:
        pid = int(conn.execute(
            "INSERT INTO produtos_cadastro (nome, sku, ean, preco, unidade_venda, ativo)"
            " VALUES ('Tijolo','TIJ-01','7891000000009',1.0,'UN',1) RETURNING id"
        ).fetchone()["id"])
        conn.commit()
    r = c.post("/api/compras/cotacoes", headers=h, json={
        "apelido": "Cotação Tijolos",
        "comprador": "Loja",
        "itens": [{"produto_id": pid, "quantidade": 1000}],
        "fornecedores": [{"fornecedor_id": fid}],
    })
    cid = r.get_json()["id"]
    token = r.get_json()["invites"][0]["token"]
    c.post(f"/api/fornecedor/{token}/proposta", json={
        "precos": [{"cotacao_item_id": 1, "preco_unitario": 1.5, "disponibilidade_estoque": 1}],
        "condicao_pagamento": "30/60/90",
        "condicao_pagamento_dias": 90,
    })
    rp = c.post(f"/api/compras/cotacoes/{cid}/pedidos", headers=h, json={"logica": "fracionado"})
    pedido_id = rp.get_json()["pedidos"][0]["id"]

    rr = c.post(f"/api/compras/pedidos/{pedido_id}/receber", headers=h,
                json={"condicao_pagamento_id": cond})
    assert rr.status_code == 200, rr.get_json()
    assert rr.get_json()["parcelas"] == 3
    with system_conn() as conn:
        contas = conn.execute(
            "SELECT * FROM contas_pagar WHERE origem_tipo='pedido_compra' AND origem_id=%s ORDER BY parcela",
            (pedido_id,),
        ).fetchall()
    assert len(contas) == 3
    assert all(x["origem_tipo"] == "pedido_compra" for x in contas)
    assert len({x["grupo_id"] for x in contas}) == 1  # mesmo grupo


def test_venda_a_prazo_com_grupo_e_origem(system_db):
    c, h = _admin_client(system_db)
    cond = _condicao_30_60_90()
    from catalog_server.repositories import cliente_repo

    cliente_repo.garantir_padrao()
    with system_conn() as conn:
        conn.execute("SELECT setval('clientes_id_seq', GREATEST((SELECT COALESCE(MAX(id),1) FROM clientes), 1))")
        conn.commit()
    cid = cliente_repo.create({"nome": "Cliente Grupo", "tipo_pessoa": "f", "limite_credito": 9000})
    _aprovar_credito(c, h, cid)
    r = c.post("/api/orcamentos", headers=h, json={
        "cliente": "Cliente Grupo",
        "cliente_id": cid,
        "condicao_pagamento_id": cond,
        "itens": [{"produto_id": 1, "nome": "Produto", "quantidade": 1, "preco_unitario": 3000.0}],
    })
    oid = r.get_json()["id"]
    rf = c.patch(f"/api/orcamentos/{oid}", headers=h, json={"status": "finalizado"})
    assert rf.status_code == 200, rf.get_json()
    with system_conn() as conn:
        contas = conn.execute(
            "SELECT * FROM contas_receber WHERE origem_tipo='venda' AND origem_id=%s ORDER BY parcela",
            (oid,),
        ).fetchall()
    assert len(contas) == 3
    assert [x["parcela"] for x in contas] == [1, 2, 3]
    assert len({x["grupo_id"] for x in contas}) == 1
