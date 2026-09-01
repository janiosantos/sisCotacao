"""Infraestrutura (ARC-003/005/006 + INT-001/006 + ADM-003 LGPD)."""
from __future__ import annotations

from catalog_server import auth_token, permissao
from catalog_server.app_factory import create_app
from catalog_server.db import system_conn
from catalog_server.services import conciliacao, comunicacao, infra, lgpd, reconciliacao


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


# ─── ARC-003: idempotência ─────────────────────────────────

def test_idempotencia_retry(system_db):
    chamadas = []
    def fn(conn):
        chamadas.append(1)
        return {"ok": True, "n": len(chamadas)}
    r1 = infra.executar("chave-1", "teste", {"a": 1}, fn)
    r2 = infra.executar("chave-1", "teste", {"a": 1}, fn)
    assert r1["duplicado"] is False
    assert r2["duplicado"] is True
    assert len(chamadas) == 1  # fn rodou uma vez


def test_idempotencia_payload_diferente_rejeita(system_db):
    def fn(conn):
        return {"ok": True}
    infra.executar("chave-2", "teste", {"a": 1}, fn)
    try:
        infra.executar("chave-2", "teste", {"a": 2}, fn)
        assert False
    except ValueError as exc:
        assert "payload diferente" in str(exc)


# ─── ARC-006: auditoria ────────────────────────────────────

def test_auditoria_mascara_pii(system_db):
    uid = _usuario("aud")
    infra.registrar("alterar_preco", "produto", 5, antes={"preco": 10.0, "cliente_doc": "12345678901"},
                    depois={"preco": 12.0, "cliente_doc": "12345678901"},
                    ator_id=uid, ator_login="aud", ip="127.0.0.1", correlation_id="abc-1")
    ev = infra.listar(alvo_tipo="produto", alvo_id=5)
    assert len(ev) == 1
    assert ev[0]["correlation_id"] == "abc-1"
    # PII mascarada
    assert ev[0]["antes"]["cliente_doc"] != "12345678901"
    assert "***" in ev[0]["antes"]["cliente_doc"]


# ─── LGPD (ADM-003) ────────────────────────────────────────

def test_lgpd_mascarar():
    assert lgpd.mascarar("123.456.789-01") != "123.456.789-01"
    assert "***" in lgpd.mascarar("joao@exemplo.com")
    assert lgpd.mascarar_valor("senha_hash", "abc123") != "abc123"
    assert lgpd.mascarar_valor("nome", "João") == "João"  # não sensível


# ─── ARC-005: reconciliação ────────────────────────────────

def test_reconciliacao(system_db):
    d = reconciliacao.divergencias()
    assert "resumo" in d
    assert "saldo_inconsistente" in d


# ─── INT-001: conciliação bancária ─────────────────────────

def test_importar_e_sugerir(system_db):
    conta = conciliacao.criar_conta("Banco X", "001", "12345")
    r = conciliacao.importar_extrato(conta, [
        {"data": "2026-08-01", "descricao": "TED recebido", "valor": 100.0, "documento": "PG-1"},
    ])
    assert r["importados"] == 1
    # importar de novo (idempotente)
    r2 = conciliacao.importar_extrato(conta, [
        {"data": "2026-08-01", "descricao": "TED recebido", "valor": 100.0, "documento": "PG-1"},
    ])
    assert r2["importados"] == 0
    assert len(conciliacao.listar(conta)) == 1


def test_aprovar_baixa_conta(system_db):
    conta = conciliacao.criar_conta("Banco X")
    with system_conn() as conn:
        cid = int(conn.execute("INSERT INTO clientes (nome, doc, tipo_pessoa) VALUES (%s,%s,%s) RETURNING id", ("C", "1", "F")).fetchone()["id"])
        cr = int(conn.execute(
            "INSERT INTO contas_receber (cliente, cliente_id, descricao, valor, saldo, data_vencimento, data_emissao, status)"
            " VALUES (%s,%s,%s,100,100,%s,%s,'aberto') RETURNING id",
            ("C", cid, "Venda", "2026-09-01", "2026-08-01"),
        ).fetchone()["id"])
        conn.commit()
    conciliacao.importar_extrato(conta, [{"data": "2026-08-05", "descricao": "Depósito", "valor": 100.0, "documento": "DEP"}])
    sugs = conciliacao.sugerir_matching(conta)
    assert len(sugs) == 1
    uid = _usuario("conc")
    conciliacao.aprovar(sugs[0]["movimento_id"], uid)
    with system_conn() as conn:
        st = conn.execute("SELECT status FROM contas_receber WHERE id=%s", (cr,)).fetchone()
    assert st["status"] == "pago"


def test_rejeitar(system_db):
    conta = conciliacao.criar_conta("Banco X")
    conciliacao.importar_extrato(conta, [{"data": "2026-08-05", "descricao": "Sem match", "valor": 1.5}])
    mov = conciliacao.listar(conta)[0]
    conciliacao.rejeitar(mov["id"])
    assert conciliacao.listar(conta)[0]["status"] == "rejeitado"


# ─── INT-006: comunicação via outbox ───────────────────────

def test_comunicacao_agenda(system_db):
    oid = comunicacao.agendar("whatsapp", "5511998887777", "pedido_confirmacao", {"pedido": 1}, chave_idempotencia="msg-1", origem="pedido")
    assert oid > 0
    envios = comunicacao.listar_envios()
    assert any(e["id"] == oid and e["tipo"] == "whatsapp" for e in envios)
    assert "****" in envios[0]["destinatario"]  # mascarado


# ─── API ───────────────────────────────────────────────────

def test_api_infra(system_db):
    uid = _usuario("infra_api")
    with system_conn() as conn:
        conn.execute(
            "INSERT INTO usuario_perfis (usuario_id, perfil_id) SELECT %s, id FROM perfis WHERE nome='Administrador'",
            (uid,),
        )
        conn.commit()
    permissao.invalidar(uid)
    client = create_app().test_client()
    h = {"Authorization": f"Bearer {auth_token.criar_token({'id': uid, 'login': 'infra_api'})}"}
    assert client.get("/api/infra/reconciliacao", headers=h).status_code == 200
    assert client.get("/api/infra/auditoria", headers=h).status_code == 200
    assert client.get("/api/infra/comunicacao", headers=h).status_code == 200
    r = client.post("/api/infra/contas-bancarias", headers=h, json={"banco": "Banco Y"})
    assert r.status_code == 201