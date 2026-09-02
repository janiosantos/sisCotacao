"""Regressões do crediário aprovado e da segregação entre venda e caixa."""
from __future__ import annotations

from datetime import date, timedelta

from werkzeug.security import generate_password_hash

from catalog_server import auth_token, permissao
from catalog_server.app_factory import create_app
from catalog_server.db import system_conn
from catalog_server.repositories import cliente_repo


def _perfil(nome: str) -> int:
    with system_conn() as conn:
        return int(conn.execute("SELECT id FROM perfis WHERE nome=?", (nome,)).fetchone()["id"])


def _usuario(login: str, perfil: str) -> tuple[int, dict]:
    with system_conn() as conn:
        uid = int(conn.execute(
            "INSERT INTO usuarios (nome, login, senha_hash) VALUES (?,?,?) RETURNING id",
            (login, login, generate_password_hash("x123")),
        ).fetchone()["id"])
        conn.execute("INSERT INTO usuario_perfis (usuario_id, perfil_id) VALUES (?,?)", (uid, _perfil(perfil)))
    permissao.invalidar(uid)
    return uid, {"Authorization": f"Bearer {auth_token.criar_token({'id': uid, 'login': login})}"}


def _cliente(nome: str = "Cliente Teste") -> int:
    cliente_repo.garantir_padrao()
    with system_conn() as conn:
        conn.execute("SELECT setval('clientes_id_seq', GREATEST((SELECT COALESCE(MAX(id),1) FROM clientes), 1))")
    return cliente_repo.create({"nome": nome, "tipo_pessoa": "f", "limite_credito": 5000})


def _condicao_prazo() -> int:
    with system_conn() as conn:
        cid = int(conn.execute(
            "INSERT INTO condicoes_pagamento (nome, descricao, ativo) VALUES (?,?,1) RETURNING id",
            ("30 dias", "teste"),
        ).fetchone()["id"])
        conn.execute(
            "INSERT INTO condicao_parcelas (condicao_id, sequencia, dias, percentual) VALUES (?,?,?,?)",
            (cid, 1, 30, 100),
        )
    return cid


def _aprovar(c, admin_header: dict, cliente_id: int, limite: float = 5000, condicoes: list[str] | None = None) -> None:
    payload = {
        "limite_aprovado": limite,
        "prazo_maximo_dias": 30,
        "vigencia_inicio": date.today().isoformat(),
        "vigencia_fim": (date.today() + timedelta(days=365)).isoformat(),
        "motivo": "Análise cadastral inicial",
    }
    if condicoes is not None:
        payload["condicoes_permitidas"] = condicoes
    r = c.post(f"/api/clientes/{cliente_id}/credito/aprovar", headers=admin_header, json=payload)
    assert r.status_code == 200, r.get_json()


def test_solicitacao_aprovacao_e_historico(system_db):
    c = create_app().test_client()
    admin_id, admin = _usuario("admincredito", "Administrador")
    vendedor_id, vendedor = _usuario("vendedorcredito", "Vendedor")
    cliente_id = _cliente()

    r = c.post(f"/api/clientes/{cliente_id}/credito/solicitar", headers=vendedor, json={"motivo": "Cliente recorrente"})
    assert r.status_code == 201, r.get_json()
    assert r.get_json()["status"] == "em_analise"

    r = c.post(f"/api/clientes/{cliente_id}/credito/aprovar", headers=vendedor, json={})
    assert r.status_code == 403
    _aprovar(c, admin, cliente_id)

    situacao = c.get(f"/api/clientes/{cliente_id}/credito", headers=vendedor)
    assert situacao.status_code == 200
    assert situacao.get_json()["aprovado"] is True
    assert situacao.get_json()["limite_aprovado"] == 5000
    historico = c.get(f"/api/clientes/{cliente_id}/credito/historico", headers=admin)
    assert historico.status_code == 200
    assert [e["tipo_evento"] for e in historico.get_json()["eventos"]][:2] == ["aprovacao", "solicitacao"]


def test_cliente_padrao_nao_aceita_prazo(system_db):
    c = create_app().test_client()
    _, vendedor = _usuario("vendedorpadrao", "Vendedor")
    condicao = _condicao_prazo()
    r = c.post("/api/orcamentos", headers=vendedor, json={
        "cliente_id": 1,
        "cliente": "CONSUMIDOR",
        "condicao_pagamento_id": condicao,
        "itens": [{"produto_id": 1, "nome": "Produto", "quantidade": 1, "preco_unitario": 10}],
    })
    assert r.status_code == 403
    assert r.get_json()["code"] == "cliente_padrao_somente_avista"


def test_venda_a_prazo_exige_aprovacao(system_db):
    c = create_app().test_client()
    _, vendedor = _usuario("vendedorprazo", "Vendedor")
    cliente_id = _cliente("Cliente sem aprovação")
    condicao = _condicao_prazo()
    r = c.post("/api/orcamentos", headers=vendedor, json={
        "cliente_id": cliente_id,
        "cliente": "Cliente sem aprovação",
        "condicao_pagamento_id": condicao,
        "itens": [{"produto_id": 1, "nome": "Produto", "quantidade": 1, "preco_unitario": 10}],
    })
    assert r.status_code == 201
    r = c.patch(f"/api/orcamentos/{r.get_json()['id']}", headers=vendedor, json={"status": "finalizado"})
    assert r.status_code == 403
    assert r.get_json()["code"] == "crediario_nao_aprovado"


def test_venda_respeita_condicoes_permitidas_no_credito(system_db):
    c = create_app().test_client()
    _, vendedor = _usuario("vendedorprazo2", "Vendedor")
    _, admin = _usuario("admincredito2", "Administrador")
    cliente_id = _cliente("Cliente com condição restrita")
    condicao = _condicao_prazo()
    _aprovar(c, admin, cliente_id, condicoes=["999999"])
    r = c.post("/api/orcamentos", headers=vendedor, json={
        "cliente_id": cliente_id,
        "cliente": "Cliente com condição restrita",
        "condicao_pagamento_id": condicao,
        "itens": [{"produto_id": 1, "nome": "Produto", "quantidade": 1, "preco_unitario": 10}],
    })
    assert r.status_code == 201
    r = c.patch(f"/api/orcamentos/{r.get_json()['id']}", headers=vendedor, json={"status": "finalizado"})
    assert r.status_code == 403
    assert r.get_json()["code"] == "condicao_credito_nao_permitida"


def test_vendedor_nao_recebe_e_operador_recebe(system_db):
    c = create_app().test_client()
    vendedor_id, vendedor = _usuario("vendedorrecebe", "Vendedor")
    _, operador = _usuario("operadorrecebe", "Operador")
    r = c.post("/api/orcamentos", headers=vendedor, json={
        "cliente": "CONSUMIDOR",
        "cliente_id": 1,
        "itens": [{"produto_id": 1, "nome": "Produto", "quantidade": 1, "preco_unitario": 10}],
    })
    assert r.status_code == 201
    oid = r.get_json()["id"]
    assert c.patch(f"/api/orcamentos/{oid}", headers=vendedor, json={"status": "finalizado"}).status_code == 200
    r = c.post(f"/api/orcamentos/{oid}/receber", headers=vendedor, json={"valor_recebido": 10, "forma_pagamento": "dinheiro"})
    assert r.status_code == 403
    assert r.get_json()["code"] in {"recebimento_permissao_negada", "Permissão negada"} or "permiss" in r.get_json().get("error", "").lower()
    r = c.post(f"/api/orcamentos/{oid}/receber", headers=operador, json={"valor_recebido": 10, "forma_pagamento": "dinheiro"})
    assert r.status_code == 200, r.get_json()
    assert r.get_json()["recebido"] is True


def test_recebimento_retry_idempotente_nao_duplica_caixa(system_db):
    c = create_app().test_client()
    vendedor_id, vendedor = _usuario("vendedoridemp", "Vendedor")
    _, operador = _usuario("operadoridemp", "Operador")
    r = c.post("/api/orcamentos", headers=vendedor, json={
        "cliente": "CONSUMIDOR",
        "cliente_id": 1,
        "itens": [{"produto_id": 1, "nome": "Produto", "quantidade": 1, "preco_unitario": 25}],
    })
    oid = r.get_json()["id"]
    assert c.patch(f"/api/orcamentos/{oid}", headers=vendedor, json={"status": "finalizado"}).status_code == 200
    chave = "recebimento-teste-idempotente"
    headers = {**operador, "Idempotency-Key": chave}
    payload = {"valor_recebido": 25, "forma_pagamento": "dinheiro"}
    primeira = c.post(f"/api/orcamentos/{oid}/receber", headers=headers, json=payload)
    segunda = c.post(f"/api/orcamentos/{oid}/receber", headers=headers, json=payload)
    assert primeira.status_code == 200, primeira.get_json()
    assert segunda.status_code == 200, segunda.get_json()
    assert segunda.get_json() == primeira.get_json()
    with system_conn() as conn:
        movimentos = conn.execute(
            "SELECT COUNT(*) AS n FROM caixa_movimento WHERE orcamento_id=?", (oid,)
        ).fetchone()
    assert int(movimentos["n"]) == 1
