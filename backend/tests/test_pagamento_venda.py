"""Pagamentos por pedido (VEN-003): entidade, idempotência, troco só em dinheiro, estorno."""
from __future__ import annotations

from catalog_server import auth_token, permissao
from catalog_server.app_factory import create_app
from catalog_server.db import system_conn
from catalog_server.services import pagamento_venda


def _cliente(system_db) -> int:
    with system_conn() as conn:
        cid = int(conn.execute("INSERT INTO clientes (nome, doc, tipo_pessoa) VALUES (%s,%s,%s) RETURNING id", ("C", "1", "F")).fetchone()["id"])
        conn.commit()
        return cid


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


def _orcamento_finalizado(system_db, total: float = 100.0) -> int:
    cid = _cliente(system_db)
    import uuid

    numero = f"PG-{uuid.uuid4().hex[:8]}"
    with system_conn() as conn:
        oid = int(conn.execute(
            "INSERT INTO orcamentos (cliente_id, numero, status, cliente, total, subtotal, criado_em)"
            " VALUES (%s,%s,'finalizado',%s,%s,%s,%s) RETURNING id",
            (cid, numero, "Cliente", total, total, "2026-08-10 10:00:00"),
        ).fetchone()["id"])
        conn.commit()
        return oid


def test_dinheiro_confirma_e_marca_pago(system_db):
    oid = _orcamento_finalizado(system_db)
    r = pagamento_venda.registrar(oid, [{"forma": "dinheiro", "valor": 100.0}])
    assert r["total_pagamentos"] == 100.0
    assert r["pendentes"] == 0
    with system_conn() as conn:
        st = conn.execute("SELECT status FROM orcamentos WHERE id=%s", (oid,)).fetchone()
    assert st["status"] == "recebido"


def test_cartao_pendente_nao_marca_pago(system_db):
    oid = _orcamento_finalizado(system_db)
    r = pagamento_venda.registrar(oid, [{"forma": "cartao_credito", "valor": 100.0, "bandeira": "VISA", "provedor": "asaas"}])
    assert r["pendentes"] == 1
    with system_conn() as conn:
        st = conn.execute("SELECT status FROM orcamentos WHERE id=%s", (oid,)).fetchone()
    assert st["status"] == "finalizado"  # pendente não marca paga
    pagamento_venda.confirmar(oid)
    with system_conn() as conn:
        st = conn.execute("SELECT status FROM orcamentos WHERE id=%s", (oid,)).fetchone()
    assert st["status"] == "recebido"


def test_soma_excede_rejeita(system_db):
    oid = _orcamento_finalizado(system_db, total=100.0)
    try:
        pagamento_venda.registrar(oid, [{"forma": "cartao_credito", "valor": 150.0}])
        assert False
    except ValueError as exc:
        assert "excede" in str(exc)


def test_troco_so_dinheiro(system_db):
    oid = _orcamento_finalizado(system_db, total=100.0)
    pagamento_venda.registrar(oid, [{"forma": "dinheiro", "valor": 120.0}])
    c = pagamento_venda.confirmar(oid)
    assert c["troco"] == 20.0
    # troco só dinheiro: cartão que passa do total é rejeitado no registrar
    oid2 = _orcamento_finalizado(system_db, total=100.0)
    try:
        pagamento_venda.registrar(oid2, [{"forma": "cartao_credito", "valor": 120.0}])
        assert False
    except ValueError as exc:
        assert "troco só em dinheiro" in str(exc)


def test_retry_nao_duplica(system_db):
    oid = _orcamento_finalizado(system_db)
    r1 = pagamento_venda.registrar(oid, [{"forma": "dinheiro", "valor": 100.0}], idempotency_key="pg-1")
    pagamento_venda.registrar(oid, [{"forma": "dinheiro", "valor": 100.0}], idempotency_key="pg-1")
    with system_conn() as conn:
        n = conn.execute("SELECT COUNT(*) FROM orcamento_pagamento WHERE orcamento_id=%s", (oid,)).fetchone()
    assert n["count"] == 1


def test_estornar_reverte(system_db):
    oid = _orcamento_finalizado(system_db)
    r = pagamento_venda.registrar(oid, [{"forma": "pix", "valor": 100.0}])
    pagamento_venda.confirmar(oid)
    p = pagamento_venda.listar(oid)[0]
    pagamento_venda.estornar(p["id"])
    with system_conn() as conn:
        st = conn.execute("SELECT status FROM orcamentos WHERE id=%s", (oid,)).fetchone()
        pg = conn.execute("SELECT status FROM orcamento_pagamento WHERE id=%s", (p["id"],)).fetchone()
    assert pg["status"] == "estornado"
    assert st["status"] == "finalizado"  # volta para finalizado


def test_api_pagamentos(system_db):
    oid = _orcamento_finalizado(system_db)
    uid = _usuario("pg_api")
    with system_conn() as conn:
        conn.execute(
            "INSERT INTO usuario_perfis (usuario_id, perfil_id) SELECT %s, id FROM perfis WHERE nome='Administrador'",
            (uid,),
        )
        conn.commit()
    permissao.invalidar(uid)
    client = create_app().test_client()
    h = {"Authorization": f"Bearer {auth_token.criar_token({'id': uid, 'login': 'pg_api'})}"}
    r = client.post(f"/api/orcamentos/{oid}/pagamentos", headers=h, json={"pagamentos": [{"forma": "dinheiro", "valor": 100}]})
    assert r.status_code == 200, r.get_json()
    assert client.get(f"/api/orcamentos/{oid}/pagamentos", headers=h).status_code == 200
    pg = client.get(f"/api/orcamentos/{oid}/pagamentos", headers=h).get_json()["pagamentos"][0]
    r = client.post(f"/api/orcamentos/pagamentos/{pg['id']}/estornar", headers=h)
    assert r.status_code == 200