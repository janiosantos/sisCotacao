"""Cadastro completo de fornecedores (v2.19.0, B).

Cobre o CRUD expandido (campos de endereço, categoria, condições, avaliação),
a tabela de contatos (`fornecedor_contatos`) e a busca por termo/categoria.
"""
from __future__ import annotations

from catalog_server import auth_token
from catalog_server.db import system_conn
from catalog_server.app_factory import create_app


def _usuario(login: str) -> int:
    from werkzeug.security import generate_password_hash

    with system_conn() as conn:
        cur = conn.execute(
            "INSERT INTO usuarios (nome, login, senha_hash, desconto_limite_pct)"
            " VALUES (%s,%s,%s,5)",
            ("Admin", login, generate_password_hash("x123")),
        )
        uid = int(cur.lastrowid)
        conn.commit()
    return uid


def _perfil_id(nome: str) -> int:
    with system_conn() as conn:
        return int(conn.execute(
            "SELECT id FROM perfis WHERE nome=%s", (nome,)
        ).fetchone()["id"])


def _vincular(uid: int, perfil: str) -> None:
    from catalog_server import permissao

    with system_conn() as conn:
        conn.execute(
            "INSERT INTO usuario_perfis (usuario_id, perfil_id) VALUES (%s,%s) ON CONFLICT DO NOTHING",
            (uid, _perfil_id(perfil)),
        )
        conn.commit()
    permissao.invalidar(uid)


def _admin_client(system_db):
    uid = _usuario("admf")
    _vincular(uid, "Administrador")
    c = create_app().test_client()
    h = {"Authorization": f"Bearer {auth_token.criar_token({'id': uid, 'login': 'admf'})}"}
    return c, h


def test_fornecedor_crud_completo(system_db):
    c, h = _admin_client(system_db)
    payload = {
        "nome": "Casa das Ferramentas",
        "razao_social": "Casa das Ferramentas Ltda",
        "cnpj_cpf": "12345678000199",
        "representante": "Carlos",
        "telefone": "1130004000",
        "whatsapp": "11987654321",
        "email": "contato@casafer.com",
        "endereco": "Rua das Ferramentas",
        "numero": "100",
        "bairro": "Centro",
        "cidade": "São Paulo",
        "uf": "SP",
        "cep": "01001000",
        "categoria": "ferramentas",
        "condicao_pagamento_id": None,
        "prazo_entrega_dias": 15,
        "nota": 4.5,
        "observacoes": "Bom atendimento",
    }
    r = c.post("/api/fornecedores", headers=h, json=payload)
    assert r.status_code in (200, 201), r.get_json()
    fid = r.get_json()["id"]

    d = c.get(f"/api/fornecedores/{fid}", headers=h)
    assert d.status_code == 200
    body = d.get_json()
    assert body["categoria"] == "ferramentas"
    assert body["prazo_entrega_dias"] == 15
    assert body["cidade"] == "São Paulo"
    assert float(body["nota"]) == 4.5

    payload["nota"] = 5.0
    u = c.put(f"/api/fornecedores/{fid}", headers=h, json=payload)
    assert u.status_code == 200, u.get_json()
    assert float(c.get(f"/api/fornecedores/{fid}", headers=h).get_json()["nota"]) == 5.0


def test_fornecedor_contatos(system_db):
    c, h = _admin_client(system_db)
    r = c.post("/api/fornecedores", headers=h, json={"nome": "Fornecedor Contatos"})
    fid = r.get_json()["id"]

    ctt = c.post(f"/api/fornecedores/{fid}/contatos", headers=h,
                 json={"nome": "João", "cargo": "Vendas", "telefone": "11999990000", "email": "joao@x.com"})
    assert ctt.status_code == 201, ctt.get_json()
    ctid = ctt.get_json()["id"]

    lista = c.get(f"/api/fornecedores/{fid}/contatos", headers=h)
    assert lista.status_code == 200
    assert len(lista.get_json()) == 1
    assert lista.get_json()[0]["nome"] == "João"

    rmv = c.delete(f"/api/fornecedores/contatos/{ctid}", headers=h)
    assert rmv.status_code == 200
    assert len(c.get(f"/api/fornecedores/{fid}/contatos", headers=h).get_json()) == 0


def test_fornecedor_busca_por_termo_e_categoria(system_db):
    c, h = _admin_client(system_db)
    c.post("/api/fornecedores", headers=h, json={"nome": "Ferragens do Norte", "categoria": "ferramentas", "cidade": "Manaus"})
    c.post("/api/fornecedores", headers=h, json={"nome": "Tintas Color", "categoria": "tintas", "cidade": "Recife"})

    r = c.get("/api/fornecedores?q=Manaus", headers=h)
    assert r.status_code == 200
    nomes = [f["nome"] for f in r.get_json()]
    assert "Ferragens do Norte" in nomes
    assert "Tintas Color" not in nomes

    r2 = c.get("/api/fornecedores?categoria=tintas", headers=h)
    nomes2 = [f["nome"] for f in r2.get_json()]
    assert "Tintas Color" in nomes2


def test_fornecedor_contexto_categorias(system_db):
    c, h = _admin_client(system_db)
    r = c.get("/api/fornecedores/contexto", headers=h)
    assert r.status_code == 200
    body = r.get_json()
    cats = [x["valor"] for x in body["categorias"]]
    assert "ferramentas" in cats
    assert "elétrico" in cats