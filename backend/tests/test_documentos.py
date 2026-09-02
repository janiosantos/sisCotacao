from werkzeug.security import generate_password_hash

from catalog_server import auth_token, permissao
from catalog_server.app_factory import create_app
from catalog_server.db import system_conn
from catalog_server.services.documentos import (
    normalizar_e_validar_documento,
    normalizar_tipo_pessoa,
    validar_cnpj,
    validar_cpf,
)


def _admin_header() -> dict[str, str]:
    with system_conn() as conn:
        uid = int(conn.execute(
            "INSERT INTO usuarios (nome, login, senha_hash) VALUES (?,?,?) RETURNING id",
            ("Admin documentos", "admin-documentos", generate_password_hash("x123")),
        ).fetchone()["id"])
        pid = int(conn.execute("SELECT id FROM perfis WHERE nome='Administrador'").fetchone()["id"])
        conn.execute("INSERT INTO usuario_perfis (usuario_id, perfil_id) VALUES (?,?)", (uid, pid))
    permissao.invalidar(uid)
    return {"Authorization": f"Bearer {auth_token.criar_token({'id': uid, 'login': 'admin-documentos'})}"}


def test_validar_cnpj_formatado_e_digitos():
    assert validar_cnpj("04.252.011/0001-10") is True
    assert validar_cnpj("04252011000110") is True


def test_rejeitar_cnpj_invalido_e_repetido():
    assert validar_cnpj("04.252.011/0001-11") is False
    assert validar_cnpj("11.111.111/1111-11") is False


def test_validar_cpf_mantem_regra_existente():
    assert validar_cpf("529.982.247-25") is True
    assert validar_cpf("529.982.247-26") is False


def test_normalizar_documento_preserva_tipo_juridico():
    assert normalizar_tipo_pessoa("J") == "j"
    assert normalizar_e_validar_documento("04.252.011/0001-10", "J") == ("j", "04252011000110")


def test_api_persiste_cnpj_atualizado_e_rejeita_invalido(system_db):
    client = create_app().test_client()
    header = _admin_header()

    response = client.post("/api/clientes", headers=header, json={
        "nome": "Empresa CNPJ",
        "tipo_pessoa": "J",
        "doc": "04.252.011/0001-10",
    })
    assert response.status_code == 201, response.get_json()
    cliente = client.get(f"/api/clientes/{response.get_json()['id']}", headers=header).get_json()
    assert cliente["tipo_pessoa"] == "j"
    assert cliente["doc"] == "04252011000110"

    response = client.post("/api/clientes", headers=header, json={
        "nome": "Empresa CNPJ invalido",
        "tipo_pessoa": "j",
        "doc": "04.252.011/0001-11",
    })
    assert response.status_code == 400
    assert response.get_json()["code"] == "documento_invalido"
