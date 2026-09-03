"""Cadastro simples de parceiro + extrato com vendas + indicação no PDV."""
from __future__ import annotations

from catalog_server import auth_token, permissao
from catalog_server.app_factory import create_app
from catalog_server.db import system_conn
from catalog_server.services import parceiros


def _usuario(login: str, perfil: str) -> tuple[int, dict]:
    from werkzeug.security import generate_password_hash

    with system_conn() as conn:
        cur = conn.execute(
            "INSERT INTO usuarios (nome, login, senha_hash) VALUES (%s,%s,%s)",
            ("User " + login, login, generate_password_hash("x123")),
        )
        uid = int(cur.lastrowid)
        perfil_id = int(conn.execute("SELECT id FROM perfis WHERE nome=%s", (perfil,)).fetchone()["id"])
        conn.execute(
            "INSERT INTO usuario_perfis (usuario_id, perfil_id) VALUES (%s,%s) ON CONFLICT DO NOTHING",
            (uid, perfil_id),
        )
        conn.commit()
    permissao.invalidar(uid)
    return uid, {"Authorization": f"Bearer {auth_token.criar_token({'id': uid, 'login': login})}"}


def _garantir_perfil_parceiros(perfil: str, acoes: list[str]) -> None:
    import json

    with system_conn() as conn:
        conn.execute(
            "INSERT INTO perfis (nome, descricao) VALUES (%s,%s) ON CONFLICT (nome) DO NOTHING",
            (perfil, "Perfil"),
        )
        conn.execute(
            "INSERT INTO recursos (codigo, nome, grupo) VALUES ('parceiros','Parceiros e fidelização','Comercial') "
            "ON CONFLICT (codigo) DO NOTHING"
        )
        pid = int(conn.execute("SELECT id FROM perfis WHERE nome=%s", (perfil,)).fetchone()["id"])
        rid = int(conn.execute("SELECT id FROM recursos WHERE codigo='parceiros'").fetchone()["id"])
        conn.execute(
            "INSERT INTO perfil_recurso (perfil_id, recurso_id, acoes) VALUES (%s,%s,%s::jsonb) "
            "ON CONFLICT (perfil_id, recurso_id) DO NOTHING",
            (pid, rid, json.dumps(acoes)),
        )
        conn.commit()


def _admin():
    return _usuario("admpar", "Administrador")


def _novo_parceiro_simples() -> int:
    return parceiros.criar(
        "eletricista",
        nome="João da Silva",
        apelido="João",
        cpf="11122233344",
        telefone="(11) 1234-5678",
        whatsapp="(11) 91234-5678",
        email="joao@exemplo.com",
    )["id"]


def test_cadastro_simples_sem_cliente(system_db):
    p = parceiros.criar(
        "encanador", nome="Maria Souza", apelido="Maria", cpf="99988877766"
    )
    assert p["cliente_id"] is None
    assert p["nome"] == "Maria Souza"
    assert p["apelido"] == "Maria"
    assert p["status"] == "pendente"
    with system_conn() as conn:
        row = conn.execute(
            "SELECT nome, apelido, cpf, cliente_id FROM parceiro_profissional WHERE id=?", (p["id"],)
        ).fetchone()
    assert row["cliente_id"] is None
    assert row["cpf"] == "99988877766"


def test_cadastro_simples_exige_nome(system_db):
    try:
        parceiros.criar("eletricista")
        assert False, "deveria exigir nome"
    except ValueError:
        pass


def test_dedup_por_cpf(system_db):
    p1 = parceiros.criar("eletricista", nome="A", cpf="11122233344")
    p2 = parceiros.criar("eletricista", nome="B", cpf="11122233344")
    assert p2["duplicado"] is True
    assert p2["id"] == p1["id"]


def test_listar_parceiro_simples(system_db):
    pid = _novo_parceiro_simples()
    encontrados = parceiros.listar(status="pendente", termo="João")
    assert any(p["id"] == pid and p["cliente_nome"] == "João da Silva" for p in encontrados)


def test_ledger_inclui_vendas_indicadas(system_db):
    from werkzeug.security import generate_password_hash

    with system_conn() as conn:
        uid = int(conn.execute(
            "INSERT INTO usuarios (nome, login, senha_hash) VALUES (%s,%s,%s) RETURNING id",
            ("Operador", "opledger", generate_password_hash("x")),
        ).fetchone()["id"])
        cliente_id = int(conn.execute(
            "INSERT INTO clientes (nome, doc, tipo_pessoa, segmento) VALUES (%s,%s,%s,%s) RETURNING id",
            ("Cliente indicado", "12345678901", "F", "profissional"),
        ).fetchone()["id"])
        venda_id = int(conn.execute(
            "INSERT INTO orcamentos (cliente, cliente_id, numero, status, total, total_liquido, desconto, usuario_id) "
            "VALUES (%s,%s,%s,'recebido',500,500,0,%s) RETURNING id",
            ("Cliente indicado", cliente_id, "PV-PAR-S", uid),
        ).fetchone()["id"])
        conn.commit()
    pid = _novo_parceiro_simples()
    parceiros.alterar_status(pid, "ativo")
    ind = parceiros.criar_indicacao(pid, cliente_id)
    parceiros.converter_indicacao(ind["id"], venda_id, usuario_id=uid)
    ledger = parceiros.ledger(pid)
    assert len(ledger["vendas"]) == 1
    v = ledger["vendas"][0]
    assert v["orcamento_id"] == venda_id
    assert v["cliente_nome"] == "Cliente indicado"
    assert float(v["total"]) == 500.0
    assert v["numero"] == "PV-PAR-S"
    assert ledger["parceiro"]["nome_exibicao"] == "João"


def test_api_cadastro_simples(system_db):
    _, h = _admin()
    client = create_app().test_client()
    r = client.post("/api/parceiros", headers=h, json={
        "categoria": "eletricista",
        "nome": "Carlos Lima",
        "apelido": "Carlão",
        "cpf": "12312312300",
        "telefone": "(11) 5555-0000",
        "whatsapp": "(11) 99999-0000",
        "email": "carlos@exemplo.com",
    })
    assert r.status_code == 201
    body = r.get_json()
    assert body["cliente_id"] is None
    assert body["nome"] == "Carlos Lima"


def test_api_orcamento_parceiro_id_vinca_indicacao(system_db):
    _, h = _admin()
    client = create_app().test_client()
    pid = _novo_parceiro_simples()
    parceiros.alterar_status(pid, "ativo")

    r = client.post("/api/orcamentos", headers=h, json={
        "cliente": "Consumidor",
        "cliente_id": 1,
        "status": "rascunho",
        "itens": [{"produto_id": None, "nome": "Item", "quantidade": 1, "preco_unitario": 100, "desconto_percentual": 0}],
        "parceiro_id": pid,
    })
    assert r.status_code == 201, r.get_data(as_text=True)
    orc_id = r.get_json()["id"]
    with system_conn() as conn:
        row = conn.execute("SELECT indicacao_id FROM orcamentos WHERE id=?", (orc_id,)).fetchone()
        status = conn.execute(
            "SELECT status FROM parceiro_indicacao WHERE id=?", (row["indicacao_id"],)
        ).fetchone()
    assert row["indicacao_id"] is not None
    assert status["status"] == "registrada"


def test_rbac_extrato_restrito_admin_financeiro(system_db):
    pid = _novo_parceiro_simples()
    _garantir_perfil_parceiros("Financeiro", ["visualizar", "aprovar"])
    client = create_app().test_client()
    # Financeiro pode visualizar o extrato.
    _, h_fin = _usuario("finpar", "Financeiro")
    r = client.get(f"/api/parceiros/{pid}/ledger", headers=h_fin)
    assert r.status_code == 200
    # Vendedor (sem parceiros.visualizar após a 0155) não pode.
    _, h_ven = _usuario("vendpar", "Vendedor")
    r = client.get(f"/api/parceiros/{pid}/ledger", headers=h_ven)
    assert r.status_code == 403


def test_api_indicacao_disponivel_para_pre_venda(system_db):
    pid = _novo_parceiro_simples()
    parceiros.alterar_status(pid, "ativo")
    _, h_ven = _usuario("vendpv", "Vendedor")
    client = create_app().test_client()
    r = client.get("/api/parceiros/indicacao", headers=h_ven)
    assert r.status_code == 200
    assert any(p["id"] == pid for p in r.get_json()["parceiros"])