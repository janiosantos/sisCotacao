"""Busca administrativa, taxonomia e edicao rapida do cadastro de produtos."""

from __future__ import annotations

from werkzeug.security import generate_password_hash

from catalog_server import auth_token, permissao
from catalog_server.app_factory import create_app
from catalog_server.db import system_conn


def _cliente_admin():
    with system_conn() as conn:
        usuario_id = int(
            conn.execute(
                "INSERT INTO usuarios (nome, login, senha_hash) VALUES (?,?,?) RETURNING id",
                ("Admin produtos", "admin_produtos", generate_password_hash("teste")),
            ).fetchone()["id"]
        )
        conn.execute(
            "INSERT INTO usuario_perfis (usuario_id, perfil_id)"
            " SELECT ?, id FROM perfis WHERE nome='Administrador'",
            (usuario_id,),
        )
    permissao.invalidar(usuario_id)
    token = auth_token.criar_token({"id": usuario_id, "login": "admin_produtos"})
    return create_app().test_client(), {"Authorization": f"Bearer {token}"}


def _taxonomia(prefixo: str = "ELE") -> dict:
    with system_conn() as conn:
        grupo_id = int(
            conn.execute(
                "INSERT INTO grupos (codigo, nome) VALUES (?,?) RETURNING id",
                (prefixo, f"Grupo {prefixo}"),
            ).fetchone()["id"]
        )
        subgrupo_id = int(
            conn.execute(
                "INSERT INTO subgrupos (grupo_id, codigo, nome) VALUES (?,?,?) RETURNING id",
                (grupo_id, f"{prefixo}SUB", f"Subgrupo {prefixo}"),
            ).fetchone()["id"]
        )
        categoria_id = int(
            conn.execute(
                "INSERT INTO categorias (nome, subgrupo_id) VALUES (?,?) RETURNING id",
                (f"Categoria {prefixo}", subgrupo_id),
            ).fetchone()["id"]
        )
        subcategoria_id = int(
            conn.execute(
                "INSERT INTO subcategorias (categoria_id, nome) VALUES (?,?) RETURNING id",
                (categoria_id, f"Subcategoria {prefixo}"),
            ).fetchone()["id"]
        )
    return {
        "grupo_id": grupo_id,
        "subgrupo_id": subgrupo_id,
        "categoria_id": categoria_id,
        "subcategoria_id": subcategoria_id,
    }


def _produto(nome: str, status: str, taxonomia: dict, marca: str = "Marca Teste") -> int:
    ativo = 1 if status == "publicado" else 0
    with system_conn() as conn:
        return int(
            conn.execute(
                "INSERT INTO produtos_cadastro"
                " (nome, descricao, marca, preco, unidade_venda, status_cadastro, ativo,"
                " grupo_id, subgrupo_id, categoria_id, subcategoria_id)"
                " VALUES (?,?,?,?,?,?,?,?,?,?,?) RETURNING id",
                (
                    nome, "", marca, 10, "UN", status, ativo,
                    taxonomia["grupo_id"], taxonomia["subgrupo_id"],
                    taxonomia["categoria_id"], taxonomia["subcategoria_id"],
                ),
            ).fetchone()["id"]
        )


def test_busca_administrativa_encontra_nome_marca_e_todos_status(system_db):
    taxonomia = _taxonomia()
    rascunho_id = _produto("Lampada LED Industrial", "rascunho", taxonomia, "Fabrica Acao")
    publicado_id = _produto("Tomada de embutir", "publicado", taxonomia)
    client, headers = _cliente_admin()

    por_nome = client.get("/api/produtos-cadastro?q=lampada", headers=headers)
    por_marca_sem_acento = client.get("/api/produtos-cadastro?q=acao", headers=headers)
    todos = client.get("/api/produtos-cadastro", headers=headers)
    publicados = client.get("/api/produtos-cadastro?status_cadastro=publicado", headers=headers)

    assert por_nome.status_code == 200
    assert [item["id"] for item in por_nome.get_json()["items"]] == [rascunho_id]
    assert [item["id"] for item in por_marca_sem_acento.get_json()["items"]] == [rascunho_id]
    assert {item["id"] for item in todos.get_json()["items"]} == {rascunho_id, publicado_id}
    assert [item["id"] for item in publicados.get_json()["items"]] == [publicado_id]


def test_filtros_hierarquicos_usam_ids(system_db):
    taxonomia_a = _taxonomia("ELE")
    taxonomia_b = _taxonomia("HID")
    produto_a = _produto("Produto eletrico", "rascunho", taxonomia_a)
    _produto("Produto hidraulico", "rascunho", taxonomia_b)
    client, headers = _cliente_admin()

    for campo in ("grupo_id", "subgrupo_id", "categoria_id", "subcategoria_id"):
        resposta = client.get(
            f"/api/produtos-cadastro?{campo}={taxonomia_a[campo]}", headers=headers
        )
        assert resposta.status_code == 200
        assert [item["id"] for item in resposta.get_json()["items"]] == [produto_a]


def test_edicao_lote_atualiza_campos_status_e_auditoria(system_db):
    taxonomia = _taxonomia()
    produto_id = _produto("Produto original", "rascunho", taxonomia)
    client, headers = _cliente_admin()
    item = client.get("/api/produtos-cadastro", headers=headers).get_json()["items"][0]

    resposta = client.patch(
        "/api/produtos-cadastro/lote",
        headers=headers,
        json={
            "items": [{
                "id": produto_id,
                "versao_edicao": item["versao_edicao"],
                "nome": "Produto revisado",
                "marca": "Nova Marca",
                "preco": 25.90,
                "unidade_venda": "CX",
                "grupo_id": taxonomia["grupo_id"],
                "subgrupo_id": taxonomia["subgrupo_id"],
                "categoria_id": taxonomia["categoria_id"],
                "subcategoria_id": taxonomia["subcategoria_id"],
                "status_cadastro": "publicado",
            }]
        },
    )

    assert resposta.status_code == 200, resposta.get_json()
    with system_conn() as conn:
        produto = conn.execute(
            "SELECT nome, marca, preco, unidade_venda, status_cadastro, ativo"
            " FROM produtos_cadastro WHERE id=?",
            (produto_id,),
        ).fetchone()
        auditoria = conn.execute(
            "SELECT acao FROM auditoria_evento WHERE alvo_tipo='produto' ORDER BY id DESC LIMIT 1"
        ).fetchone()
    assert produto["nome"] == "Produto revisado"
    assert float(produto["preco"]) == 25.90
    assert produto["unidade_venda"] == "CX"
    assert produto["status_cadastro"] == "publicado"
    assert produto["ativo"] == 1
    assert auditoria["acao"] == "produtos.edicao_lote"


def test_edicao_concorrente_cancela_o_lote_inteiro(system_db):
    taxonomia = _taxonomia()
    primeiro_id = _produto("Primeiro", "rascunho", taxonomia)
    segundo_id = _produto("Segundo", "rascunho", taxonomia)
    client, headers = _cliente_admin()
    items = client.get("/api/produtos-cadastro", headers=headers).get_json()["items"]
    por_id = {item["id"]: item for item in items}
    with system_conn() as conn:
        conn.execute(
            "UPDATE produtos_cadastro SET atualizado_em='2099-01-01 00:00:00' WHERE id=?",
            (segundo_id,),
        )

    payload = []
    for produto_id, nome in ((primeiro_id, "Primeiro alterado"), (segundo_id, "Segundo alterado")):
        item = por_id[produto_id]
        payload.append({
            "id": produto_id,
            "versao_edicao": item["versao_edicao"],
            "nome": nome,
            "marca": item["marca"],
            "preco": item["preco"],
            "unidade_venda": item["unidade_venda"],
            "grupo_id": item["grupo_id"],
            "subgrupo_id": item["subgrupo_id"],
            "categoria_id": item["categoria_id"],
            "subcategoria_id": item["subcategoria_id"],
            "status_cadastro": item["status_cadastro"],
        })
    resposta = client.patch("/api/produtos-cadastro/lote", headers=headers, json={"items": payload})

    assert resposta.status_code == 409
    assert resposta.get_json()["code"] == "edicao_concorrente"
    with system_conn() as conn:
        nome = conn.execute("SELECT nome FROM produtos_cadastro WHERE id=?", (primeiro_id,)).fetchone()["nome"]
    assert nome == "Primeiro"


def test_hierarquia_invalida_cancela_edicao(system_db):
    taxonomia_a = _taxonomia("ELE")
    taxonomia_b = _taxonomia("HID")
    produto_id = _produto("Produto", "rascunho", taxonomia_a)
    client, headers = _cliente_admin()
    item = client.get("/api/produtos-cadastro", headers=headers).get_json()["items"][0]
    item.update({
        "versao_edicao": item["versao_edicao"],
        "subgrupo_id": taxonomia_b["subgrupo_id"],
        "categoria_id": taxonomia_a["categoria_id"],
    })

    resposta = client.patch("/api/produtos-cadastro/lote", headers=headers, json={"items": [item]})

    assert resposta.status_code == 400
    with system_conn() as conn:
        subgrupo_id = conn.execute(
            "SELECT subgrupo_id FROM produtos_cadastro WHERE id=?", (produto_id,)
        ).fetchone()["subgrupo_id"]
    assert subgrupo_id == taxonomia_a["subgrupo_id"]


def test_exclusao_logica_sincroniza_status_e_ativo(system_db):
    taxonomia = _taxonomia()
    produto_id = _produto("Produto publicado", "publicado", taxonomia)
    client, headers = _cliente_admin()

    resposta = client.delete(f"/api/produtos-cadastro/{produto_id}", headers=headers)

    assert resposta.status_code == 200
    with system_conn() as conn:
        produto = conn.execute(
            "SELECT status_cadastro, ativo FROM produtos_cadastro WHERE id=?", (produto_id,)
        ).fetchone()
    assert produto["status_cadastro"] == "bloqueado"
    assert produto["ativo"] == 0
