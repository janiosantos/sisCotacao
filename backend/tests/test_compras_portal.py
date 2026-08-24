"""Portal de compras do fornecedor rico (v2.20.0).

Cobre o fluxo de cotação de compras (tela única):
- criação da cotação grava unidade_solicitada do produto;
- portal_itens sugere unidade/fator da variante para o representante;
- submit_proposta grava unidade_compra, fator_conversao, marca_ofertada,
  motivo_indisponibilidade e observacao por item;
- montar_matriz propaga preco_embalagem, qtd_embalagens e motivo;
- lembrar/reenvio regenera link/whatsapp de um fornecedor pendente.
"""
from __future__ import annotations

from catalog_server import auth_token
from catalog_server.db import system_conn
from catalog_server.app_factory import create_app


def _usuario(login: str, limite_pct: float = 5.0) -> int:
    from werkzeug.security import generate_password_hash

    with system_conn() as conn:
        cur = conn.execute(
            "INSERT INTO usuarios (nome, login, senha_hash, desconto_limite_pct)"
            " VALUES (%s,%s,%s,%s)",
            ("Comprador", login, generate_password_hash("x123"), limite_pct),
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


def _cliente_comprador(system_db):
    uid = _usuario("compras")
    from catalog_server import permissao

    with system_conn() as conn:
        conn.execute(
            "INSERT INTO usuario_perfis (usuario_id, perfil_id) VALUES (%s,%s) ON CONFLICT DO NOTHING",
            (uid, _perfil_id("Administrador")),
        )
        conn.commit()
    permissao.invalidar(uid)
    c = create_app().test_client()
    h = _token(uid, "compras")
    return c, h


def _variante_com_unidade(system_db) -> int:
    """Cria um produto com variante (unidade_venda=CX, fator=12)."""
    with system_conn() as conn:
        conn.execute(
            "INSERT INTO produtos_cadastro (nome, ativo) VALUES ('Parafuso Zincado', 1)"
        )
        pid = int(conn.execute("SELECT lastval()").fetchone()["lastval"])
        conn.execute(
            "INSERT INTO variantes (produto_id, sku, ean, preco, unidade_venda, fator_conversao, ativo)"
            " VALUES (%s,'PAR-ZIN-12','7891000000001',0.5,'CX',12,1)",
            (pid,),
        )
        vid = int(conn.execute("SELECT lastval()").fetchone()["lastval"])
        conn.commit()
        return vid


def _fornecedor(nome: str = "Distribuidora X") -> int:
    from catalog_server.repositories import supplier_repo

    return supplier_repo.create({"nome": nome, "whatsapp": "5511999990000", "email": "rep@x.com"})


def _criar_cotacao(client, header, vid: int, fid: int) -> str:
    """Cria cotação com 1 item e devolve o token do fornecedor."""
    r = client.post("/api/compras/cotacoes", headers=header, json={
        "apelido": "Cotação Teste",
        "comprador": "Loja",
        "data_limite": "2026-12-31",
        "itens": [{"produto_id": vid, "quantidade": 30}],
        "fornecedores": [{"fornecedor_id": fid}],
    })
    assert r.status_code == 200, r.get_json()
    invites = r.get_json()["invites"]
    assert len(invites) == 1
    return invites[0]["token"]


def test_portal_itens_sugere_unidade_da_variante(system_db):
    vid = _variante_com_unidade(system_db)
    fid = _fornecedor()
    c, h = _cliente_comprador(system_db)
    token = _criar_cotacao(c, h, vid, fid)

    dados = c.get(f"/api/fornecedor/{token}")
    assert dados.status_code == 200
    itens = dados.get_json()["itens"]
    assert len(itens) == 1
    assert itens[0]["unidade_compra"] == "CX"
    assert float(itens[0]["fator_conversao"]) == 12


def test_submit_proposta_grava_unidade_marca_motivo(system_db):
    vid = _variante_com_unidade(system_db)
    fid = _fornecedor()
    c, h = _cliente_comprador(system_db)
    token = _criar_cotacao(c, h, vid, fid)

    r = c.post(f"/api/fornecedor/{token}/proposta", json={
        "precos": [{
            "cotacao_item_id": 1,
            "preco_unitario": 4.5,
            "desconto": 5,
            "prazo_entrega_dias": 10,
            "disponibilidade_estoque": 1,
            "unidade_compra": "CX",
            "fator_conversao": 12,
            "marca_ofertada": "Zincado Plus",
            "observacao": "Caixa fechada, frete incluso",
        }],
        "condicao_pagamento": "30 dias",
        "condicao_pagamento_dias": 30,
    })
    assert r.status_code == 200, r.get_json()

    with system_conn() as conn:
        cp = conn.execute("SELECT * FROM cotacao_precos WHERE cotacao_item_id=1").fetchone()
    assert float(cp["fator_conversao"]) == 12
    assert cp["unidade_compra"] == "CX"
    assert cp["marca_ofertada"] == "Zincado Plus"
    assert cp["motivo_indisponibilidade"] == ""
    assert cp["observacao"] == "Caixa fechada, frete incluso"


def test_submit_indisponivel_grava_motivo(system_db):
    vid = _variante_com_unidade(system_db)
    fid = _fornecedor()
    c, h = _cliente_comprador(system_db)
    token = _criar_cotacao(c, h, vid, fid)

    r = c.post(f"/api/fornecedor/{token}/proposta", json={
        "precos": [{
            "cotacao_item_id": 1,
            "preco_unitario": 0,
            "disponibilidade_estoque": 0,
            "motivo_indisponibilidade": "em_falta_estoque",
            "unidade_compra": "CX",
            "fator_conversao": 12,
            "marca_ofertada": "",
        }],
        "condicao_pagamento": "À vista",
        "condicao_pagamento_dias": 0,
    })
    assert r.status_code == 200, r.get_json()
    with system_conn() as conn:
        cp = conn.execute("SELECT * FROM cotacao_precos WHERE cotacao_item_id=1").fetchone()
    assert cp["motivo_indisponibilidade"] == "em_falta_estoque"
    assert int(cp["disponibilidade_estoque"]) == 0


def test_matriz_propaga_preco_embalagem_e_motivo(system_db):
    vid = _variante_com_unidade(system_db)
    fid = _fornecedor()
    c, h = _cliente_comprador(system_db)
    token = _criar_cotacao(c, h, vid, fid)

    c.post(f"/api/fornecedor/{token}/proposta", json={
        "precos": [{
            "cotacao_item_id": 1,
            "preco_unitario": 4.0,
            "desconto": 0,
            "prazo_entrega_dias": 7,
            "disponibilidade_estoque": 1,
            "unidade_compra": "CX",
            "fator_conversao": 12,
            "marca_ofertada": "Zincado Plus",
        }],
        "condicao_pagamento": "À vista",
        "condicao_pagamento_dias": 0,
    })

    m = c.get("/api/compras/cotacoes/1/comparar", headers=h)
    assert m.status_code == 200
    itens = m.get_json()["itens"]
    assert len(itens) == 1
    pr = itens[0]["precos"][str(fid)]
    assert pr["unidade_compra"] == "CX"
    assert float(pr["fator_conversao"]) == 12
    assert pr["marca_ofertada"] == "Zincado Plus"
    assert pr["preco_embalagem"] == 48.0
    assert pr["qtd_embalagens"] == 3  # ceil(30/12)


def test_lembrar_fornecedor_gera_whatsapp(system_db):
    vid = _variante_com_unidade(system_db)
    fid = _fornecedor("Distribuidora Z")
    c, h = _cliente_comprador(system_db)
    token = _criar_cotacao(c, h, vid, fid)

    r = c.get(f"/api/compras/cotacoes/1/lembrar/{fid}", headers=h)
    assert r.status_code == 200
    body = r.get_json()
    assert body["fornecedor_id"] == fid
    assert body["nome"] == "Distribuidora Z"
    assert "wa.me/5511999990000" in body["whatsapp_url"]
    assert body["link"] and "/fornecedor/" in body["link"]


def test_lembrar_inexistente_404(system_db):
    vid = _variante_com_unidade(system_db)
    fid = _fornecedor()
    c, h = _cliente_comprador(system_db)
    _criar_cotacao(c, h, vid, fid)
    r = c.get("/api/compras/cotacoes/1/lembrar/9999", headers=h)
    assert r.status_code == 404