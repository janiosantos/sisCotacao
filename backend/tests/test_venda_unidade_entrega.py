"""Unidade de venda (VEN-001) e retirada/entrega (VEN-005)."""
from __future__ import annotations

from catalog_server import auth_token, permissao
from catalog_server.app_factory import create_app
from catalog_server.db import system_conn
from catalog_server.services import venda_entrega


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


def _cliente(system_db) -> int:
    with system_conn() as conn:
        cid = int(conn.execute("INSERT INTO clientes (nome, doc, tipo_pessoa) VALUES (%s,%s,%s) RETURNING id", ("C", "1", "F")).fetchone()["id"])
        conn.commit()
        return cid


def _orcamento_finalizado(system_db) -> tuple[int, int]:
    cid = _cliente(system_db)
    with system_conn() as conn:
        conn.execute("INSERT INTO produtos_cadastro (nome, ativo, sku, preco, unidade_venda, fator_conversao) VALUES (%s,%s,%s,%s,%s,%s)", ("Cabo", 1, "VU-1", 10.0, "CX", 100))
        pid = int(conn.execute("SELECT lastval()").fetchone()["lastval"])
        conn.execute("INSERT INTO unidade_conversao (produto_id, unidade_origem, unidade_destino, fator, unidade_base) VALUES (%s,'CX','UN',100,'UN')", (pid,))
        oid = int(conn.execute(
            "INSERT INTO orcamentos (cliente_id, numero, status, cliente, criado_em) VALUES (%s,%s,'finalizado',%s,%s) RETURNING id",
            (cid, "VU-O1", "Cliente", "2026-08-10 10:00:00"),
        ).fetchone()["id"])
        conn.execute(
            "INSERT INTO orcamento_itens (orcamento_id, produto_id, nome, quantidade, preco_unitario, subtotal)"
            " VALUES (%s,%s,%s,%s,%s,%s)", (oid, pid, "Cabo", 100, 10.0, 1000.0),
        )
        conn.commit()
        return oid, pid


def test_unidade_de_venda_converte(system_db):
    cid = _cliente(system_db)
    with system_conn() as conn:
        conn.execute("INSERT INTO produtos_cadastro (nome, ativo, sku, preco, unidade_venda, fator_conversao) VALUES (%s,%s,%s,%s,%s,%s)", ("Cabo", 1, "VU-1", 10.0, "CX", 100))
        pid = int(conn.execute("SELECT lastval()").fetchone()["lastval"])
        conn.execute("INSERT INTO unidade_conversao (produto_id, unidade_origem, unidade_destino, fator, unidade_base) VALUES (%s,'CX','UN',100,'UN')", (pid,))
        oid = int(conn.execute(
            "INSERT INTO orcamentos (cliente_id, numero, status, cliente, criado_em) VALUES (%s,%s,'ativo',%s,%s) RETURNING id",
            (cid, "VU-O1", "Cliente", "2026-08-10 10:00:00"),
        ).fetchone()["id"])
        conn.commit()
    # substitui item vendendo 2 CX (fator 100) → 200 unidades base
    from catalog_server.repositories.orcamentos import orcamento_repo
    orcamento_repo.substituir_itens(oid, [{"produto_id": pid, "nome": "Cabo", "quantidade": 2, "preco_unitario": 500.0, "unidade": "CX"}])
    with system_conn() as conn:
        it = conn.execute("SELECT quantidade, unidade_vendida, fator_venda FROM orcamento_itens WHERE orcamento_id=%s", (oid,)).fetchone()
    assert float(it["quantidade"]) == 200.0  # convertido para base
    assert it["unidade_vendida"] == "CX"
    assert float(it["fator_venda"]) == 100.0


def test_configurar_entrega(system_db):
    oid, _ = _orcamento_finalizado(system_db)
    r = venda_entrega.configurar_entrega(oid, "entrega", "Rua X, 10", "2026-09-05")
    assert r["status_entrega"] == "pendente"
    assert venda_entrega.transicionar(oid, "enviada")["para"] == "enviada"
    assert venda_entrega.transicionar(oid, "entregue")["para"] == "entregue"


def test_balcao_retira_direto(system_db):
    oid, _ = _orcamento_finalizado(system_db)
    r = venda_entrega.configurar_entrega(oid, "balcao")
    assert venda_entrega.retirar(oid)["status_entrega"] == "entregue"


def test_entrega_sem_endereco_rejeita(system_db):
    oid, _ = _orcamento_finalizado(system_db)
    try:
        venda_entrega.configurar_entrega(oid, "entrega", None)
        assert False
    except ValueError as exc:
        assert "endereco" in str(exc)


def test_nao_transiciona_pulo(system_db):
    oid, _ = _orcamento_finalizado(system_db)
    venda_entrega.configurar_entrega(oid, "entrega", "Rua X", "2026-09-05")
    try:
        venda_entrega.transicionar(oid, "entregue")  # pendente → entregue direto é inválido p/ entrega
        assert False
    except ValueError:
        pass


def test_api_entrega(system_db):
    oid, _ = _orcamento_finalizado(system_db)
    uid = _usuario("veu_api")
    with system_conn() as conn:
        conn.execute(
            "INSERT INTO usuario_perfis (usuario_id, perfil_id) SELECT %s, id FROM perfis WHERE nome='Administrador'",
            (uid,),
        )
        conn.commit()
    permissao.invalidar(uid)
    client = create_app().test_client()
    h = {"Authorization": f"Bearer {auth_token.criar_token({'id': uid, 'login': 'veu_api'})}"}
    r = client.post(f"/api/orcamentos/{oid}/entrega", headers=h, json={"tipo_entrega": "balcao"})
    assert r.status_code == 200, r.get_json()
    r = client.post(f"/api/orcamentos/{oid}/entrega/status", headers=h, json={"status": "retirar"})
    assert r.status_code == 200
    assert client.get("/api/orcamentos/entregas", headers=h).status_code == 200