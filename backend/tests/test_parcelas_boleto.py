"""Parcelas de venda a prazo + boleto (v2.22.0).

Cobre:
- finalizar orçamento de cliente identificado com condição a prazo gera N contas a receber;
- cliente padrão (CONSUMIDOR, id 1) NÃO gera parcelas (mantém 1 conta à vista);
- gerar boleto marca as parcelas com linha digitável/código de barras;
- pedido finalizado com boleto emitido não pode ser reaberto;
- reabrir (sem boleto) estorna as contas a receber.
"""
from __future__ import annotations

from catalog_server import auth_token
from catalog_server.db import system_conn
from catalog_server.app_factory import create_app


def _usuario(login: str, limite_pct: float = 5.0, autoriza: bool = False) -> int:
    from werkzeug.security import generate_password_hash

    with system_conn() as conn:
        cur = conn.execute(
            "INSERT INTO usuarios (nome, login, senha_hash, desconto_limite_pct, autoriza_desconto)"
            " VALUES (%s,%s,%s,%s,%s)",
            ("Vendedor", login, generate_password_hash("x123"), limite_pct, 1 if autoriza else 0),
        )
        uid = int(cur.lastrowid)
        conn.commit()
    return uid


def _perfil_id(nome: str) -> int:
    with system_conn() as conn:
        return int(conn.execute(
            "SELECT id FROM perfis WHERE nome=%s", (nome,)
        ).fetchone()["id"])


def _token(usuario_id: int, login: str) -> dict:
    return {"Authorization": f"Bearer {auth_token.criar_token({'id': usuario_id, 'login': login})}"}


def _client_com_vendedor(system_db, autoriza: bool = False):
    vid = _usuario("vendedor", autoriza=autoriza)
    from catalog_server import permissao

    with system_conn() as conn:
        conn.execute(
            "INSERT INTO usuario_perfis (usuario_id, perfil_id) VALUES (%s,%s) ON CONFLICT DO NOTHING",
            (vid, _perfil_id("Vendedor")),
        )
        conn.commit()
    permissao.invalidar(vid)
    c = create_app().test_client()
    return c, vid


def _condicao(parcelas: list[tuple[int, float]]) -> int:
    """Cria condição de pagamento com parcelas (dias, percentual)."""
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


def _condicao_a_prazo() -> int:
    return _condicao([(30, 33.33), (60, 33.33), (90, 33.34)])


def _condicao_2_parcelas() -> int:
    return _condicao([(30, 50.0), (60, 50.0)])


def _cliente(nome: str) -> int:
    from catalog_server.repositories import cliente_repo

    cliente_repo.garantir_padrao()
    with system_conn() as conn:
        conn.execute(
            "SELECT setval('clientes_id_seq', GREATEST((SELECT COALESCE(MAX(id),1) FROM clientes), 1))"
        )
        conn.commit()
    return cliente_repo.create({"nome": nome, "tipo_pessoa": "f", "limite_credito": 5000})


def _orcamento(client, header, cliente_id, cliente_nome, total, condicao_id):
    r = client.post("/api/orcamentos", headers=header, json={
        "cliente": cliente_nome,
        "cliente_id": cliente_id,
        "condicao_pagamento_id": condicao_id,
        "itens": [{"produto_id": 1, "nome": "Produto", "quantidade": 1, "preco_unitario": total}],
    })
    assert r.status_code == 201, r.get_json()
    return r.get_json()["id"]


def test_finalizar_a_prazo_gera_parcelas(system_db):
    c, vid = _client_com_vendedor(system_db)
    h = _token(vid, "vendedor")
    cond = _condicao_a_prazo()
    cid = _cliente("Maria Construtora")
    oid = _orcamento(c, h, cid, "Maria Construtora", 3000.0, cond)  # 30/60/90
    r = c.patch(f"/api/orcamentos/{oid}", headers=h, json={"status": "finalizado"})
    assert r.status_code == 200, r.get_json()
    with system_conn() as conn:
        contas = conn.execute(
            "SELECT * FROM contas_receber WHERE documento=(SELECT numero FROM orcamentos WHERE id=%s) ORDER BY id",
            (oid,),
        ).fetchall()
    assert len(contas) == 3  # 3 parcelas
    soma = round(sum(float(x["valor"]) for x in contas), 2)
    assert soma == 3000.0


def test_finalizar_consumidor_nao_gera_parcelas(system_db):
    c, vid = _client_com_vendedor(system_db)
    h = _token(vid, "vendedor")
    cond = _condicao_a_prazo()
    oid = _orcamento(c, h, 1, "CONSUMIDOR", 200.0, cond)  # cliente padrão id 1
    r = c.patch(f"/api/orcamentos/{oid}", headers=h, json={"status": "finalizado"})
    assert r.status_code == 200, r.get_json()
    with system_conn() as conn:
        contas = conn.execute(
            "SELECT * FROM contas_receber WHERE documento=(SELECT numero FROM orcamentos WHERE id=%s)",
            (oid,),
        ).fetchall()
    assert len(contas) == 1  # à vista/balcão: 1 conta


def test_gerar_boleto_marca_parcelas(system_db):
    c, vid = _client_com_vendedor(system_db)
    h = _token(vid, "vendedor")
    cond = _condicao_a_prazo()
    cid = _cliente("Pedro Obra")
    oid = _orcamento(c, h, cid, "Pedro Obra", 1200.0, cond)
    c.patch(f"/api/orcamentos/{oid}", headers=h, json={"status": "finalizado"})

    r = c.post(f"/api/orcamentos/{oid}/boleto", headers=h)
    assert r.status_code == 200, r.get_json()
    boletos = r.get_json()["boletos"]
    assert len(boletos) == 3
    for b in boletos:
        assert b["status_boleto"] == "gerado"
        assert len(b["linha_digitavel"]) == 48
        assert b["codigo_barras"]


def test_reabrir_com_boleto_bloqueia(system_db):
    c, vid = _client_com_vendedor(system_db)
    h = _token(vid, "vendedor")
    cond = _condicao_2_parcelas()
    cid = _cliente("Cliente Boleto")
    oid = _orcamento(c, h, cid, "Cliente Boleto", 500.0, cond)
    c.patch(f"/api/orcamentos/{oid}", headers=h, json={"status": "finalizado"})
    c.post(f"/api/orcamentos/{oid}/boleto", headers=h)

    r = c.post(f"/api/orcamentos/{oid}/reabrir", headers=h)
    assert r.status_code == 403
    assert "boleto" in r.get_json()["error"]


def test_reabrir_sem_boleto_estorna_contas(system_db):
    c, vid = _client_com_vendedor(system_db, autoriza=True)
    h = _token(vid, "vendedor")
    cond = _condicao_2_parcelas()
    cid = _cliente("Cliente Correcao")
    oid = _orcamento(c, h, cid, "Cliente Correcao", 900.0, cond)
    c.patch(f"/api/orcamentos/{oid}", headers=h, json={"status": "finalizado"})

    r = c.post(f"/api/orcamentos/{oid}/reabrir", headers=h)
    assert r.status_code == 200, r.get_json()
    with system_conn() as conn:
        st = conn.execute("SELECT status FROM orcamentos WHERE id=%s", (oid,)).fetchone()
        contas = conn.execute(
            "SELECT * FROM contas_receber WHERE documento=(SELECT numero FROM orcamentos WHERE id=%s)",
            (oid,),
        ).fetchall()
    assert st["status"] == "liberado"
    assert all(x["status"] == "cancelado" for x in contas)