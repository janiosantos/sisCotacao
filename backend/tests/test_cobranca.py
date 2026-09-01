"""Cobrança e renegociação (VEN-006)."""
from __future__ import annotations

from catalog_server import auth_token, permissao
from catalog_server.app_factory import create_app
from catalog_server.db import system_conn
from catalog_server.services import cobranca


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


def _conta_vencida(system_db, saldo: float = 100.0, vencimento: str = "2026-06-01") -> int:
    with system_conn() as conn:
        cid = int(conn.execute("INSERT INTO clientes (nome, doc, tipo_pessoa) VALUES (%s,%s,%s) RETURNING id", ("C", "1", "F")).fetchone()["id"])
        conta = int(conn.execute(
            "INSERT INTO contas_receber (cliente, cliente_id, descricao, valor, saldo, data_vencimento, data_emissao, status)"
            " VALUES (%s,%s,%s,%s,%s,%s,%s,'aberto') RETURNING id",
            ("Cliente", cid, "Venda", saldo, saldo, vencimento, "2026-05-01"),
        ).fetchone()["id"])
        conn.commit()
        return conta


def test_calcular_juros_multa(system_db):
    conta = _conta_vencida(system_db, saldo=100.0, vencimento="2026-06-01")
    r = cobranca.calcular_cobranca(conta)
    # hoje ~set/2026 → ~92 dias de atraso; juros 0.033%/dia; multa 2%
    assert r["dias_atraso"] > 0
    assert r["juros"] > 0
    assert r["multa"] == 2.0  # 100 × 2%
    assert r["juros_multa_total"] > 0
    with system_conn() as conn:
        row = conn.execute("SELECT juros_multa FROM contas_receber WHERE id=%s", (conta,)).fetchone()
    assert float(row["juros_multa"]) == r["juros_multa_total"]


def test_conta_nao_vencida_sem_cobranca(system_db):
    conta = _conta_vencida(system_db, vencimento="2099-12-31")
    r = cobranca.calcular_cobranca(conta)
    assert r["dias_atraso"] == 0
    assert r["juros_multa_total"] == 0.0


def test_renegociar_gera_parcelas(system_db):
    conta = _conta_vencida(system_db, saldo=100.0)
    r = cobranca.renegociar(conta, [{"dias": 30, "valor_pct": 50}, {"dias": 60, "valor_pct": 50}], "cliente pediu")
    assert len(r["novas_contas"]) == 2
    assert r["valor_renegociado"] > 100.0  # inclui juros/multa
    with system_conn() as conn:
        st = conn.execute("SELECT status FROM contas_receber WHERE id=%s", (conta,)).fetchone()
        nova1 = conn.execute("SELECT * FROM contas_receber WHERE id=%s", (r["novas_contas"][0],)).fetchone()
    assert st["status"] == "renegociada"
    assert nova1["renegociada_de"] == conta
    assert nova1["parcela"] == 1
    assert nova1["total_parcelas"] == 2


def test_renegociar_conta_paga_rejeita(system_db):
    conta = _conta_vencida(system_db)
    with system_conn() as conn:
        conn.execute("UPDATE contas_receber SET status='pago' WHERE id=%s", (conta,))
        conn.commit()
    try:
        cobranca.renegociar(conta, [{"dias": 30, "valor_pct": 100}])
        assert False
    except ValueError as exc:
        assert "renegociada" in str(exc) or "pago" in str(exc)


def test_listar_vencidas(system_db):
    conta = _conta_vencida(system_db)
    v = cobranca.listar_vencidas()
    assert any(c["id"] == conta for c in v)


def test_api_cobranca(system_db):
    conta = _conta_vencida(system_db)
    uid = _usuario("cob_api")
    with system_conn() as conn:
        conn.execute(
            "INSERT INTO usuario_perfis (usuario_id, perfil_id) SELECT %s, id FROM perfis WHERE nome='Administrador'",
            (uid,),
        )
        conn.commit()
    permissao.invalidar(uid)
    client = create_app().test_client()
    h = {"Authorization": f"Bearer {auth_token.criar_token({'id': uid, 'login': 'cob_api'})}"}
    r = client.post(f"/api/financeiro/cobranca/{conta}/recalcular", headers=h)
    assert r.status_code == 200, r.get_json()
    assert client.get("/api/financeiro/cobranca/vencidas", headers=h).status_code == 200
    r = client.post(f"/api/financeiro/cobranca/{conta}/renegociar", headers=h,
                    json={"novas_parcelas": [{"dias": 30, "valor_pct": 100}], "motivo": "acordo"})
    assert r.status_code == 200