"""INT-002 cobrança, ADM-001 carga inicial e ADM-002 deduplicação."""
from __future__ import annotations

from catalog_server import auth_token, permissao
from catalog_server.app_factory import create_app
from catalog_server.db import system_conn
from catalog_server.services import operacao


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


def test_status_canonico():
    assert operacao.status_canonico({"status_cobranca": "pago"}) == "pago"
    assert operacao.status_canonico({"status_cobranca": "pendente", "status": "parcial"}) == "parcial"
    assert operacao.status_canonico({"status_cobranca": "erro"}) == "erro"


def test_reconciliar_pendentes(system_db):
    with system_conn() as conn:
        cid = int(conn.execute("INSERT INTO clientes (nome, doc, tipo_pessoa) VALUES (%s,%s,%s) RETURNING id", ("C", "1", "F")).fetchone()["id"])
        conn.execute(
            "INSERT INTO contas_receber (cliente, cliente_id, descricao, valor, saldo, data_vencimento, data_emissao, status, status_cobranca)"
            " VALUES (%s,%s,%s,50,50,%s,%s,'aberto','pendente')",
            ("C", cid, "Venda", "2026-09-01", "2026-08-01"),
        )
        conn.commit()
    r = operacao.reconciliar_pendentes()
    assert len(r["pendentes"]) == 1
    assert r["pendentes"][0]["status_canonico"] == "pendente"


def test_carga_clientes_idempotente(system_db):
    r = operacao.importar_carga("clientes", [{"nome": "João", "doc": "12345678901", "whatsapp": "5511999888777"}])
    assert r["importados"] == 1
    r2 = operacao.importar_carga("clientes", [{"nome": "João", "doc": "12345678901"}])
    assert r2["importados"] == 0
    assert len(r2["rejeicoes"]) == 1  # já cadastrado
    with system_conn() as conn:
        n = conn.execute("SELECT COUNT(*) FROM clientes WHERE doc='12345678901'").fetchone()
    assert n["count"] == 1


def test_carga_rejeita_sem_doc(system_db):
    r = operacao.importar_carga("fornecedores", [{"nome": "Sem doc"}])
    assert r["importados"] == 0
    assert len(r["rejeicoes"]) == 1


def test_candidatos_sku(system_db):
    with system_conn() as conn:
        conn.execute("INSERT INTO produtos_cadastro (nome, ativo, sku) VALUES (%s,%s,%s)", ("A", 1, "DUP"))
        conn.execute("INSERT INTO produtos_cadastro (nome, ativo, sku) VALUES (%s,%s,%s)", ("B", 1, "DUP"))
        conn.commit()
    cands = operacao.candidatos("sku")
    assert any(c["sku"] == "DUP" and c["n"] >= 2 for c in cands)


def test_merge_redireciona(system_db):
    with system_conn() as conn:
        conn.execute("INSERT INTO produtos_cadastro (nome, ativo, sku) VALUES (%s,%s,%s)", ("A", 1, "M1"))
        p1 = int(conn.execute("SELECT lastval()").fetchone()["lastval"])
        conn.execute("INSERT INTO produtos_cadastro (nome, ativo, sku) VALUES (%s,%s,%s)", ("B", 1, "M2"))
        p2 = int(conn.execute("SELECT lastval()").fetchone()["lastval"])
        conn.execute("INSERT INTO estoque_saldo (produto_id, deposito_id, quantidade) VALUES (%s,1,5)", (p2,))
        conn.commit()
    operacao.merge(p1, p2, "produto")
    with system_conn() as conn:
        row = conn.execute("SELECT produto_id FROM estoque_saldo WHERE quantidade=5").fetchone()
        ev = conn.execute("SELECT COUNT(*) FROM auditoria_evento WHERE acao='merge_assistido'").fetchone()
    assert row["produto_id"] == p1  # referência redirecionada
    assert ev["count"] == 1  # auditado


def test_api_operacao(system_db):
    uid = _usuario("op_api")
    with system_conn() as conn:
        conn.execute(
            "INSERT INTO usuario_perfis (usuario_id, perfil_id) SELECT %s, id FROM perfis WHERE nome='Administrador'",
            (uid,),
        )
        conn.commit()
    permissao.invalidar(uid)
    client = create_app().test_client()
    h = {"Authorization": f"Bearer {auth_token.criar_token({'id': uid, 'login': 'op_api'})}"}
    assert client.get("/api/infra/cobrancas/pendentes", headers=h).status_code == 200
    assert client.get("/api/infra/deduplicacao/candidatos?tipo=sku", headers=h).status_code == 200
    r = client.post("/api/infra/carga", headers=h, json={"tipo": "clientes", "itens": [{"nome": "X", "doc": "111"}]})
    assert r.status_code == 200, r.get_json()


def test_readiness(system_db):
    """ADM-005: readiness expõe checks (banco/migrações/outbox) e reflete prontidão."""
    uid = _usuario("ready_api")
    with system_conn() as conn:
        conn.execute(
            "INSERT INTO usuario_perfis (usuario_id, perfil_id) SELECT %s, id FROM perfis WHERE nome='Administrador'",
            (uid,),
        )
        conn.commit()
    permissao.invalidar(uid)
    client = create_app().test_client()
    h = {"Authorization": f"Bearer {auth_token.criar_token({'id': uid, 'login': 'ready_api'})}"}
    r = client.get("/api/sistema/readiness", headers=h)
    assert r.status_code in (200, 503)  # 503 se pendências no ambiente
    assert "checks" in r.get_json()