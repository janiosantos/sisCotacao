"""Alçada de desconto (v2.18.0): lifecycle orçamento→pedido + autorização.

Cobre:
- desconto dentro da alçada não bloqueia (bug do login corrigido);
- acima da alçada → bloqueio (403) e desconto_status pendente;
- aprovador ≠ vendedor; alçada do aprovador ≥ desconto;
- edição/reabrir acima da alçada revoga + log; dentro da alçada mantém ok;
- rejeição grava status + motivo + log; fila de pendentes.
"""
from __future__ import annotations

from catalog_server import auth_token, permissao
from catalog_server.db import system_conn
from catalog_server.app_factory import create_app


def _criar_usuario(login: str, limite_pct: float, autoriza: bool = False) -> int:
    from werkzeug.security import generate_password_hash

    with system_conn() as conn:
        cur = conn.execute(
            "INSERT INTO usuarios (nome, login, senha_hash, desconto_limite_pct, autoriza_desconto)"
            " VALUES (%s,%s,%s,%s,%s)",
            ("Teste", login, generate_password_hash("x123"), limite_pct, 1 if autoriza else 0),
        )
        uid = int(cur.lastrowid)
        conn.commit()
    return uid


def _perfil_id(nome: str) -> int:
    with system_conn() as conn:
        return int(conn.execute(
            "SELECT id FROM perfis WHERE nome=%s", (nome,)
        ).fetchone()["id"])


def _vincular(usuario_id: int, nome_perfil: str) -> None:
    with system_conn() as conn:
        conn.execute(
            "INSERT INTO usuario_perfis (usuario_id, perfil_id) VALUES (%s,%s)"
            " ON CONFLICT DO NOTHING",
            (usuario_id, _perfil_id(nome_perfil)),
        )
        conn.commit()
    permissao.invalidar(usuario_id)


def _token(usuario_id: int, login: str) -> dict:
    return {"Authorization": f"Bearer {auth_token.criar_token({'id': usuario_id, 'login': login})}"}


def _criar_orcamento(client, header, itens, desconto=0.0, cliente="CONSUMIDOR"):
    r = client.post("/api/orcamentos", headers=header, json={
        "cliente": cliente,
        "itens": itens,
        "desconto": desconto,
    })
    assert r.status_code == 201, r.get_json()
    return r.get_json()["id"]


def _item(produto_id=1, qtd=10, preco=4.0, desc_pct=0.0):
    return {"produto_id": produto_id, "nome": "Produto", "quantidade": qtd,
            "preco_unitario": preco, "desconto_percentual": desc_pct}


def _vendedor_client(system_db):
    """Cria vendedor (alçada 5%) e gerente (alçada 10%, autoriza) + app client."""
    vid = _criar_usuario("vende", 5.0)
    _vincular(vid, "Vendedor")
    gid = _criar_usuario("gerente", 10.0, autoriza=True)
    _vincular(gid, "Operador")
    app = create_app()
    c = app.test_client()
    return c, vid, gid


def test_login_devolve_limite(system_db):
    """Bug: login não devolvia desconto_limite_pct ao frontend."""
    from werkzeug.security import generate_password_hash

    with system_conn() as conn:
        conn.execute(
            "INSERT INTO usuarios (nome, login, senha_hash, desconto_limite_pct)"
            " VALUES (%s,%s,%s,5)",
            ("Vendedor 01", "vendedor01", generate_password_hash("x123")),
        )
        conn.commit()
    c = create_app().test_client()
    r = c.post("/api/login", json={"login": "vendedor01", "senha": "x123"})
    assert r.status_code == 200
    body = r.get_json()
    assert body["desconto_limite_pct"] == 5


def test_desconto_dentro_da_alcada_nao_bloqueia(system_db):
    c, vid, gid = _vendedor_client(system_db)
    h = _token(vid, "vende")
    oid = _criar_orcamento(c, h, [_item(qtd=10, preco=4.0)], desconto=1.632)  # 4% de 40,8
    r = c.patch(f"/api/orcamentos/{oid}", headers=h, json={"status": "finalizado"})
    assert r.status_code == 200, r.get_json()
    with system_conn() as conn:
        st = conn.execute("SELECT status, desconto_status FROM orcamentos WHERE id=%s", (oid,)).fetchone()
    assert st["status"] == "finalizado"
    assert st["desconto_status"] == "ok"


def test_desconto_acima_da_alcada_bloqueia(system_db):
    c, vid, gid = _vendedor_client(system_db)
    h = _token(vid, "vende")
    oid = _criar_orcamento(c, h, [_item(qtd=10, preco=4.0)], desconto=2.448)  # 6% de 40,8
    r = c.patch(f"/api/orcamentos/{oid}", headers=h, json={"status": "finalizado"})
    assert r.status_code == 403
    assert r.get_json()["code"] == "desconto_exige_autorizacao"
    with system_conn() as conn:
        st = conn.execute("SELECT status, desconto_status FROM orcamentos WHERE id=%s", (oid,)).fetchone()
    assert st["status"] == "rascunho"  # não finalizou — segue em orçamento
    assert st["desconto_status"] == "pendente"


def test_autorizacao_aprovador_diferente_e_alcada(system_db):
    c, vid, gid = _vendedor_client(system_db)
    h = _token(vid, "vende")
    oid = _criar_orcamento(c, h, [_item(qtd=10, preco=4.0)], desconto=2.448)  # 6%
    # Vendedor não pode autorizar o próprio desconto
    r = c.post(f"/api/orcamentos/{oid}/autorizar-desconto", headers=h,
               json={"login": "vende", "senha": "x123"})
    assert r.status_code == 403
    # Gerente (10%) autoriza 6% — o endpoint exige token (gate), e valida as
    # credenciais do aprovador no corpo.
    r = c.post(f"/api/orcamentos/{oid}/autorizar-desconto", headers=h,
               json={"login": "gerente", "senha": "x123"})
    assert r.status_code == 200, r.get_json()
    with system_conn() as conn:
        st = conn.execute("SELECT desconto_status, desconto_autorizado FROM orcamentos WHERE id=%s", (oid,)).fetchone()
    assert st["desconto_status"] == "aprovado"
    assert st["desconto_autorizado"] == 1
    # Agora finaliza
    r = c.patch(f"/api/orcamentos/{oid}", headers=h, json={"status": "finalizado"})
    assert r.status_code == 200, r.get_json()


def test_aprovador_alcada_insuficiente(system_db):
    c, vid, gid = _vendedor_client(system_db)
    h = _token(vid, "vende")
    oid = _criar_orcamento(c, h, [_item(qtd=10, preco=4.0)], desconto=4.08)  # 10%
    # Gerente tem alçada 10% — 10% > 10? Igual, não bloqueia. Vamos usar 12%:
    oid = _criar_orcamento(c, h, [_item(qtd=10, preco=4.0)], desconto=4.896)  # 12%
    r = c.post(f"/api/orcamentos/{oid}/autorizar-desconto", headers=h,
               json={"login": "gerente", "senha": "x123"})
    assert r.status_code == 403
    assert "não cobre" in r.get_json()["error"]


def test_editar_conteudo_revoga_aprovacao_acima_da_alcada(system_db):
    c, vid, gid = _vendedor_client(system_db)
    h = _token(vid, "vende")
    oid = _criar_orcamento(c, h, [_item(qtd=10, preco=4.0)], desconto=2.448)  # 6%
    c.post(f"/api/orcamentos/{oid}/autorizar-desconto", headers=h, json={"login": "gerente", "senha": "x123"})
    # Edita cliente (conteúdo muda) → revoga
    r = c.patch(f"/api/orcamentos/{oid}", headers=h, json={"cliente": "Outro"})
    assert r.status_code == 200, r.get_json()
    with system_conn() as conn:
        st = conn.execute("SELECT desconto_status, desconto_autorizado FROM orcamentos WHERE id=%s", (oid,)).fetchone()
        log = conn.execute(
            "SELECT status, motivo FROM desconto_aprovacao_log WHERE orcamento_id=%s ORDER BY id DESC LIMIT 1",
            (oid,),
        ).fetchone()
    assert st["desconto_status"] == "pendente"
    assert st["desconto_autorizado"] == 0
    assert log["status"] == "revogado"


def test_editar_conteudo_dentro_da_alcada_mantem_ok(system_db):
    c, vid, gid = _vendedor_client(system_db)
    h = _token(vid, "vende")
    oid = _criar_orcamento(c, h, [_item(qtd=10, preco=4.0)], desconto=1.632)  # 4%
    c.patch(f"/api/orcamentos/{oid}", headers=h, json={"cliente": "Outro"})
    with system_conn() as conn:
        st = conn.execute("SELECT desconto_status FROM orcamentos WHERE id=%s", (oid,)).fetchone()
    assert st["desconto_status"] == "ok"


def test_reabrir_finalizado_revoga_e_exige_permissao(system_db):
    c, vid, gid = _vendedor_client(system_db)
    h = _token(vid, "vende")
    gh = _token(gid, "gerente")
    oid = _criar_orcamento(c, h, [_item(qtd=10, preco=4.0)], desconto=2.448)  # 6%
    c.post(f"/api/orcamentos/{oid}/autorizar-desconto", headers=h, json={"login": "gerente", "senha": "x123"})
    c.patch(f"/api/orcamentos/{oid}", headers=h, json={"status": "finalizado"})
    # Vendedor não pode reabrir (sem permissão aprovar)
    r = c.post(f"/api/orcamentos/{oid}/reabrir", headers=h)
    assert r.status_code == 403
    # Gerente reabre
    r = c.post(f"/api/orcamentos/{oid}/reabrir", headers=gh)
    assert r.status_code == 200, r.get_json()
    with system_conn() as conn:
        st = conn.execute("SELECT status, virou_pedido, desconto_status FROM orcamentos WHERE id=%s", (oid,)).fetchone()
    assert st["status"] == "liberado"
    assert st["virou_pedido"] == 0
    assert st["desconto_status"] == "pendente"  # acima da alçada, revogado


def test_rejeitar_desconto_grava_status_e_motivo(system_db):
    c, vid, gid = _vendedor_client(system_db)
    h = _token(vid, "vende")
    gh = _token(gid, "gerente")
    oid = _criar_orcamento(c, h, [_item(qtd=10, preco=4.0)], desconto=2.448)  # 6%
    r = c.post(f"/api/orcamentos/{oid}/rejeitar-desconto", headers=gh, json={"motivo": "Acima da política"})
    assert r.status_code == 200, r.get_json()
    with system_conn() as conn:
        st = conn.execute("SELECT desconto_status, desconto_rejeitado_motivo FROM orcamentos WHERE id=%s", (oid,)).fetchone()
        log = conn.execute(
            "SELECT status FROM desconto_aprovacao_log WHERE orcamento_id=%s ORDER BY id DESC LIMIT 1",
            (oid,),
        ).fetchone()
    assert st["desconto_status"] == "rejeitado"
    assert st["desconto_rejeitado_motivo"] == "Acima da política"
    assert log["status"] == "rejeitado"


def test_fila_pendentes_aprovacao(system_db):
    c, vid, gid = _vendedor_client(system_db)
    h = _token(vid, "vende")
    gh = _token(gid, "gerente")
    oid = _criar_orcamento(c, h, [_item(qtd=10, preco=4.0)], desconto=2.448)  # 6%
    # Bloqueia na finalização → desconto_status vira 'pendente'
    c.patch(f"/api/orcamentos/{oid}", headers=h, json={"status": "finalizado"})
    fila = c.get("/api/orcamentos/pendentes-aprovacao", headers=gh)
    assert fila.status_code == 200
    ids = [o["id"] for o in fila.get_json()]
    assert oid in ids


def test_finalizado_recebido_nao_revoga(system_db):
    c, vid, gid = _vendedor_client(system_db)
    h = _token(vid, "vende")
    oid = _criar_orcamento(c, h, [_item(qtd=10, preco=4.0)], desconto=1.632)  # 4%
    c.patch(f"/api/orcamentos/{oid}", headers=h, json={"status": "finalizado"})
    # Receber muda status mas NÃO revoga (transição de status, não conteúdo)
    c.post(f"/api/orcamentos/{oid}/receber", headers=h, json={
        "forma_pagamento": "dinheiro", "valor_recebido": 40.8,
    })
    with system_conn() as conn:
        st = conn.execute("SELECT status, desconto_status FROM orcamentos WHERE id=%s", (oid,)).fetchone()
    assert st["status"] == "recebido"
    assert st["desconto_status"] == "ok"