"""Workflow de cadastro e importação em lote (MDM-006)."""
from __future__ import annotations

from catalog_server import auth_token, permissao
from catalog_server.app_factory import create_app
from catalog_server.db import system_conn
from catalog_server.services import cadastro_importacao as cadastro_svc


def _usuario(login: str) -> int:
    from werkzeug.security import generate_password_hash

    with system_conn() as conn:
        cur = conn.execute(
            "INSERT INTO usuarios (nome, login, senha_hash) VALUES (%s,%s,%s)",
            ("Operador", login, generate_password_hash("x123")),
        )
        uid = int(cur.lastrowid)
        conn.commit()
    return uid


def _perfil_id(nome: str) -> int:
    with system_conn() as conn:
        return int(conn.execute("SELECT id FROM perfis WHERE nome=%s", (nome,)).fetchone()["id"])


def _token(usuario_id: int, login: str) -> dict:
    return {"Authorization": f"Bearer {auth_token.criar_token({'id': usuario_id, 'login': login})}"}


def _cliente_admin(system_db):
    uid = _usuario("impadmin")
    with system_conn() as conn:
        conn.execute(
            "INSERT INTO usuario_perfis (usuario_id, perfil_id) VALUES (%s,%s) ON CONFLICT DO NOTHING",
            (uid, _perfil_id("Administrador")),
        )
        conn.commit()
    permissao.invalidar(uid)
    return create_app().test_client(), _token(uid, "impadmin")


def _status(produto_id: int) -> str:
    with system_conn() as conn:
        return conn.execute(
            "SELECT status_cadastro FROM produtos_cadastro WHERE id=%s", (produto_id,)
        ).fetchone()["status_cadastro"]


def test_preview_valida_linhas(system_db):
    r = cadastro_svc.preview([
        {"nome": "Cabo 2,5mm", "sku": "CAB-25", "ean": "7891000000001"},
        {"nome": ""},
        {"nome": "X", "ean": "123"},
    ])
    assert r["total"] == 3
    assert r["erros"] == 2
    ok = [l for l in r["linhas"] if l["status"] == "ok"]
    assert ok[0]["ean"] == "7891000000001"


def test_importar_cria_rascunho_inativo(system_db):
    r = cadastro_svc.importar([
        {"nome": "Tubo 25mm", "sku": "TUB-25", "ean": "7891000000004"},
    ], "arquivo.json", None)
    assert r["criados"] == 1
    assert r["erros"] == 0
    assert r["duplicado"] is False
    with system_conn() as conn:
        p = conn.execute(
            "SELECT id, ativo, status_cadastro FROM produtos_cadastro WHERE sku='TUB-25'"
        ).fetchone()
    assert p["status_cadastro"] == "rascunho"
    assert p["ativo"] == 0


def test_importar_idempotente_mesmo_hash(system_db):
    itens = [{"nome": "Conexão 25", "sku": "CON-25"}]
    r1 = cadastro_svc.importar(itens, "a.json", None)
    r2 = cadastro_svc.importar(itens, "a.json", None)
    assert r1["criados"] == 1
    assert r2["duplicado"] is True
    assert r2["criados"] == 1  # retorna o resultado anterior, sem duplicar


def test_importar_dedup_por_sku(system_db):
    cadastro_svc.importar([{"nome": "Chave 12", "sku": "CH-12"}], "a.json", None)
    r = cadastro_svc.importar([{"nome": "Chave 12 (outro nome)", "sku": "CH-12"}], "b.json", None)
    assert r["atualizados"] == 1
    assert r["criados"] == 0


def test_status_transicoes(system_db):
    pid = cadastro_svc.importar([{"nome": "Parafuso", "sku": "PAR-1"}], "a.json", None)
    with system_conn() as conn:
        prod_id = int(conn.execute("SELECT id FROM produtos_cadastro WHERE sku='PAR-1'").fetchone()["id"])

    assert _status(prod_id) == "rascunho"
    cadastro_svc.set_status_cadastro(prod_id, "publicado")
    assert _status(prod_id) == "publicado"
    with system_conn() as conn:
        ativo = int(conn.execute("SELECT ativo FROM produtos_cadastro WHERE id=%s", (prod_id,)).fetchone()["ativo"])
    assert ativo == 1  # publicado = ativo

    cadastro_svc.set_status_cadastro(prod_id, "bloqueado")
    assert _status(prod_id) == "bloqueado"
    with system_conn() as conn:
        ativo = int(conn.execute("SELECT ativo FROM produtos_cadastro WHERE id=%s", (prod_id,)).fetchone()["ativo"])
    assert ativo == 0


def test_status_transicao_invalida(system_db):
    cadastro_svc.importar([{"nome": "Anel", "sku": "AN-1"}], "a.json", None)
    with system_conn() as conn:
        prod_id = int(conn.execute("SELECT id FROM produtos_cadastro WHERE sku='AN-1'").fetchone()["id"])
    try:
        cadastro_svc.set_status_cadastro(prod_id, "nao_existe")
        assert False, "status inválido deveria falhar"
    except ValueError:
        pass


def test_api_fluxo(system_db):
    client, h = _cliente_admin(system_db)

    r = client.post("/api/produtos/importar/preview", headers=h, json={"itens": [{"nome": "A", "sku": "A-1"}]})
    assert r.status_code == 200
    assert r.get_json()["total"] == 1

    r = client.post("/api/produtos/importar", headers=h, json={"arquivo_nome": "lote1.json", "itens": [{"nome": "A", "sku": "A-1"}]})
    body = r.get_json()
    assert body["criados"] == 1
    assert body["duplicado"] is False

    # reprocessar o mesmo lote -> idempotente
    r = client.post("/api/produtos/importar", headers=h, json={"arquivo_nome": "lote1.json", "itens": [{"nome": "A", "sku": "A-1"}]})
    assert r.get_json()["duplicado"] is True

    with system_conn() as conn:
        pid = int(conn.execute("SELECT id FROM produtos_cadastro WHERE sku='A-1'").fetchone()["id"])
    r = client.patch(f"/api/produtos-cadastro/{pid}/status", headers=h, json={"status_cadastro": "publicado"})
    assert r.status_code == 200
    assert r.get_json()["status_cadastro"] == "publicado"

    r = client.patch(f"/api/produtos-cadastro/{pid}/status", headers=h, json={"status_cadastro": "x"})
    assert r.status_code == 400


def test_api_rbac_negado_sem_permissao(system_db):
    uid = _usuario("impsem")
    permissao.invalidar(uid)
    client = create_app().test_client()
    h = _token(uid, "impsem")
    r = client.post("/api/produtos/importar/preview", headers=h, json={"itens": [{"nome": "X"}]})
    assert r.status_code == 403