from __future__ import annotations


def test_publico_produtos_sem_token(system_db):
    """API pública não exige token e não vaza campos internos."""
    from catalog_server.app_factory import create_app

    c = create_app().test_client()
    r = c.get("/api/publico/produtos?limit=5")
    assert r.status_code == 200
    data = r.get_json()
    assert "items" in data and "total" in data
    if data["items"]:
        item = data["items"][0]
        # Campos públicos presentes
        for campo in ("id", "nome", "marca", "preco", "imagem_url", "descricao"):
            assert campo in item
        # Campos internos NÃO vazam
        for interno in ("ncm", "fornecedores", "classe_abc", "group", "base"):
            assert interno not in item


def test_publico_produto_detalhe(system_db):
    from catalog_server.app_factory import create_app

    c = create_app().test_client()
    r = c.get("/api/publico/produtos/1")
    assert r.status_code in (200, 404)  # 404 se o produto 1 não existir no teste
    if r.status_code == 200:
        data = r.get_json()
        assert "id" in data and "nome" in data and "imagens" in data


def test_publico_categorias_sem_token(system_db):
    from catalog_server.app_factory import create_app

    c = create_app().test_client()
    r = c.get("/api/publico/categorias")
    assert r.status_code == 200


def test_publico_marcas_sem_token(system_db):
    from catalog_server.app_factory import create_app

    c = create_app().test_client()
    r = c.get("/api/publico/marcas")
    assert r.status_code == 200
    assert "marcas" in r.get_json()


def test_publico_cors(system_db):
    """Endpoints públicos respondem com CORS habilitado (site externo)."""
    from catalog_server.app_factory import create_app

    c = create_app().test_client()
    r = c.get("/api/publico/produtos?limit=1")
    assert r.headers.get("Access-Control-Allow-Origin") == "*"
    r2 = c.get("/api/produtos?limit=1")  # não-público: sem CORS
    assert r2.headers.get("Access-Control-Allow-Origin") is None


def test_publico_options_preflight(system_db):
    from catalog_server.app_factory import create_app

    c = create_app().test_client()
    r = c.options("/api/publico/produtos")
    assert r.status_code == 204