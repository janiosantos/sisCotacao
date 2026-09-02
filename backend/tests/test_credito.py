"""Trava de crédito no faturamento (v2.19.0, A4).

Cobre o gate de crédito que roda na conversão orçamento→pedido
(`PATCH /api/orcamentos/<id> status=finalizado`):

- dentro do limite disponível → finaliza normalmente;
- acima do limite (config bloquear_venda_sem_credito) → 403 sem_credito;
- cliente com conta em atraso (config bloquear_venda_com_atraso) → 403;
- cliente CONSUMIDOR (id 1, padrão) nunca é bloqueado;
- config desligada → não bloqueia mesmo acima do limite.
"""
from __future__ import annotations

from datetime import date, timedelta

from catalog_server import auth_token
from catalog_server.db import system_conn
from catalog_server.app_factory import create_app


def _usuario(login: str, limite_pct: float = 5.0) -> int:
    from werkzeug.security import generate_password_hash

    with system_conn() as conn:
        cur = conn.execute(
            "INSERT INTO usuarios (nome, login, senha_hash, desconto_limite_pct)"
            " VALUES (%s,%s,%s,%s)",
            ("Vendedor", login, generate_password_hash("x123"), limite_pct),
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


def _cliente(nome: str, limite: float, tipo: str = "f") -> int:
    from catalog_server.repositories import cliente_repo

    # Garante o cliente padrão (id 1) e ajusta a sequence para o próximo id
    # ser sempre maior que os ids reservados (1) após o TRUNCATE RESTART.
    cliente_repo.garantir_padrao()
    with system_conn() as conn:
        conn.execute(
            "SELECT setval('clientes_id_seq', GREATEST((SELECT COALESCE(MAX(id),1) FROM clientes), 1))"
        )
        conn.commit()
    return cliente_repo.create({
        "nome": nome,
        "tipo_pessoa": tipo,
        "limite_credito": limite,
    })


def _orcamento(client, header, cliente_id: int, cliente_nome: str, total: float, condicao_id: int | None = None) -> int:
    r = client.post("/api/orcamentos", headers=header, json={
        "cliente": cliente_nome,
        "cliente_id": cliente_id,
        "condicao_pagamento_id": condicao_id,
        "itens": [{"produto_id": 1, "nome": "Produto", "quantidade": 1, "preco_unitario": total}],
    })
    assert r.status_code == 201, r.get_json()
    return r.get_json()["id"]


def _condicao_prazo() -> int:
    with system_conn() as conn:
        cid = int(conn.execute(
            "INSERT INTO condicoes_pagamento (nome, descricao, ativo) VALUES (%s,%s,1) RETURNING id",
            ("30 dias", "teste"),
        ).fetchone()["id"])
        conn.execute(
            "INSERT INTO condicao_parcelas (condicao_id, sequencia, dias, percentual) VALUES (%s,1,30,100)",
            (cid,),
        )
        conn.commit()
    return cid


def _aprovar_credito(client, cliente_id: int, limite: float = 5000) -> None:
    admin_id = _usuario("adminfinanceiro")
    with system_conn() as conn:
        conn.execute(
            "INSERT INTO usuario_perfis (usuario_id, perfil_id) VALUES (%s,%s)",
            (admin_id, _perfil_id("Administrador")),
        )
        conn.commit()
    from catalog_server import permissao
    permissao.invalidar(admin_id)
    header = _token(admin_id, "adminfinanceiro")
    r = client.post(f"/api/clientes/{cliente_id}/credito/aprovar", headers=header, json={
        "limite_aprovado": limite,
        "prazo_maximo_dias": 60,
        "vigencia_inicio": date.today().isoformat(),
        "vigencia_fim": (date.today() + timedelta(days=365)).isoformat(),
        "motivo": "Aprovado para teste",
    })
    assert r.status_code == 200, r.get_json()


def _set_config(chave: str, valor: bool) -> None:
    with system_conn() as conn:
        conn.execute(
            "INSERT INTO config_loja (chave, valor, atualizado_em)"
            " VALUES (%s,%s,now()) ON CONFLICT (chave) DO UPDATE SET valor=EXCLUDED.valor",
            (chave, "1" if valor else "0"),
        )
        conn.commit()


def _client_com_vendedor() -> tuple:
    vid = _usuario("vendc")
    with system_conn() as conn:
        conn.execute(
            "INSERT INTO usuario_perfis (usuario_id, perfil_id) VALUES (%s,%s) ON CONFLICT DO NOTHING",
            (vid, _perfil_id("Vendedor")),
        )
        conn.commit()
    c = create_app().test_client()
    return c, vid


def test_credito_dentro_do_limite_finaliza(system_db):
    _set_config("bloquear_venda_sem_credito", True)
    c, vid = _client_com_vendedor()
    h = _token(vid, "vendc")
    cid = _cliente("Maria Construtora", limite=5000.0)
    cond = _condicao_prazo()
    _aprovar_credito(c, cid)
    oid = _orcamento(c, h, cid, "Maria Construtora", 3000.0, cond)
    r = c.patch(f"/api/orcamentos/{oid}", headers=h, json={"status": "finalizado"})
    assert r.status_code == 200, r.get_json()


def test_credito_acima_do_limite_bloqueia(system_db):
    _set_config("bloquear_venda_sem_credito", True)
    c, vid = _client_com_vendedor()
    h = _token(vid, "vendc")
    cid = _cliente("Pedro Obra", limite=1000.0)
    cond = _condicao_prazo()
    _aprovar_credito(c, cid, limite=1000)
    oid = _orcamento(c, h, cid, "Pedro Obra", 5000.0, cond)
    r = c.patch(f"/api/orcamentos/{oid}", headers=h, json={"status": "finalizado"})
    assert r.status_code == 403
    body = r.get_json()
    assert body["code"] == "sem_credito"
    with system_conn() as conn:
        st = conn.execute("SELECT status FROM orcamentos WHERE id=%s", (oid,)).fetchone()
    assert st["status"] == "rascunho"  # não converteu


def test_credito_consumidor_nunca_bloqueia(system_db):
    """Cliente padrão (id 1, CONSUMIDOR) passa sempre — regra de balcão."""
    _set_config("bloquear_venda_sem_credito", True)
    c, vid = _client_com_vendedor()
    h = _token(vid, "vendc")
    oid = _orcamento(c, h, 1, "CONSUMIDOR", 500000.0)
    r = c.patch(f"/api/orcamentos/{oid}", headers=h, json={"status": "finalizado"})
    assert r.status_code == 200, r.get_json()


def test_credito_aprovacao_obrigatoria_independe_config(system_db):
    _set_config("bloquear_venda_sem_credito", False)
    c, vid = _client_com_vendedor()
    h = _token(vid, "vendc")
    cid = _cliente("Fulano", limite=100.0)
    cond = _condicao_prazo()
    oid = _orcamento(c, h, cid, "Fulano", 9999.0, cond)
    r = c.patch(f"/api/orcamentos/{oid}", headers=h, json={"status": "finalizado"})
    assert r.status_code == 403, r.get_json()
    assert r.get_json()["code"] == "crediario_nao_aprovado"


def test_credito_atraso_bloqueia(system_db):
    _set_config("bloquear_venda_com_atraso", True)
    c, vid = _client_com_vendedor()
    h = _token(vid, "vendc")
    cid = _cliente("Cliente Atrasado", limite=5000.0)
    cond = _condicao_prazo()
    _aprovar_credito(c, cid)
    with system_conn() as conn:
        conn.execute(
            "INSERT INTO contas_receber (cliente_id, cliente, descricao, valor, saldo,"
            " data_vencimento, status)"
            " VALUES (%s,'Cliente Atrasado','Parcela vencida',100.0,100.0,'2020-01-01','aberto')",
            (cid,),
        )
        conn.commit()
    oid = _orcamento(c, h, cid, "Cliente Atrasado", 100.0, cond)
    r = c.patch(f"/api/orcamentos/{oid}", headers=h, json={"status": "finalizado"})
    assert r.status_code == 403
    assert r.get_json()["code"] == "cliente_atraso"
