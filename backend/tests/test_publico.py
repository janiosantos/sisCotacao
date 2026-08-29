from __future__ import annotations


def test_publico_produtos_sem_token(system_db):
    """API pública não exige token e não vaza campos internos."""
    from catalog_server.app_factory import create_app

    c = create_app().test_client()
    r = c.get("/api/publico/produtos?limit=5")
    assert r.status_code == 200
    data = r.get_json()
    assert "items" in data and "total" in data
    assert "offset" in data and "limit" in data and "has_more" in data
    assert len(data["items"]) <= 5
    if data["items"]:
        item = data["items"][0]
        # Campos públicos presentes
        for campo in ("id", "nome", "marca", "preco", "imagem_url", "descricao"):
            assert campo in item
        # Campos internos NÃO vazam
        for interno in ("ncm", "fornecedores", "classe_abc", "group", "base"):
            assert interno not in item


def test_publico_produtos_paginacao(system_db):
    """Paginação: limit/offset respeitados e has_more sinaliza próxima página."""
    from catalog_server.app_factory import create_app

    c = create_app().test_client()
    r1 = c.get("/api/publico/produtos?limit=2&offset=0")
    d1 = r1.get_json()
    assert len(d1["items"]) <= 2
    if d1["total"] > 2:
        assert d1["has_more"] is True
    r2 = c.get("/api/publico/produtos?limit=2&offset=2")
    d2 = r2.get_json()
    ids1 = {i["id"] for i in d1["items"]}
    ids2 = {i["id"] for i in d2["items"]}
    assert ids1.isdisjoint(ids2) or not ids2  # páginas diferentes (ou fim)
    # limite máximo respeitado
    r3 = c.get("/api/publico/produtos?limit=9999")
    assert len(r3.get_json()["items"]) <= 100


def test_publico_produtos_busca(system_db):
    """O mesmo endpoint faz pesquisa por texto via ?q=."""
    from catalog_server.app_factory import create_app

    c = create_app().test_client()
    r = c.get("/api/publico/produtos?q=nao_existe_xyz_123&limit=5")
    assert r.status_code == 200
    assert r.get_json()["total"] == 0


def test_publico_produtos_filtro_grupo(system_db):
    """Filtro por grupo (código ou nome) na listagem pública."""
    from catalog_server import db
    from catalog_server.app_factory import create_app

    with db.system_conn() as conn:
        for cod, nome in (("ELE", "ELETRICO"), ("HID", "HIDRAULICO")):
            conn.execute(
                "INSERT INTO grupos (codigo, nome) VALUES (?, ?) ON CONFLICT (codigo) DO NOTHING",
                (cod, nome),
            )
        g_ele = conn.execute("SELECT id FROM grupos WHERE codigo='ELE'").fetchone()["id"]
        g_hid = conn.execute("SELECT id FROM grupos WHERE codigo='HID'").fetchone()["id"]
        conn.execute(
            "INSERT INTO produtos_cadastro (nome, sku, ativo, preco, grupo_id)"
            " VALUES ('Cabo 10mm ELE', 'ELE-1', 1, 50, ?)",
            (g_ele,),
        )
        conn.execute(
            "INSERT INTO produtos_cadastro (nome, sku, ativo, preco, grupo_id)"
            " VALUES ('Registro HID', 'HID-1', 1, 30, ?)",
            (g_hid,),
        )

    c = create_app().test_client()
    r = c.get("/api/publico/produtos?grupo=ELE&limit=10")
    assert r.status_code == 200
    data = r.get_json()
    assert data["total"] >= 1
    for item in data["items"]:
        assert item["grupo"] == "ELE"
        assert item["grupo_nome"] == "ELETRICO"
    # por nome (case-insensitive)
    r2 = c.get("/api/publico/produtos?grupo=hidraulico&limit=10")
    d2 = r2.get_json()
    assert d2["total"] >= 1
    for item in d2["items"]:
        assert item["grupo"] == "HID"


def test_publico_grupos(system_db):
    """Lista de grupos públicos (código, nome, total)."""
    from catalog_server import db
    from catalog_server.app_factory import create_app

    with db.system_conn() as conn:
        conn.execute(
            "INSERT INTO grupos (codigo, nome) VALUES ('ELE', 'ELETRICO') ON CONFLICT (codigo) DO NOTHING"
        )
        gid = conn.execute("SELECT id FROM grupos WHERE codigo='ELE'").fetchone()["id"]
        conn.execute(
            "INSERT INTO produtos_cadastro (nome, sku, ativo, grupo_id)"
            " VALUES ('Cabo 10mm', 'ELE-9', 1, ?)",
            (gid,),
        )

    c = create_app().test_client()
    r = c.get("/api/publico/grupos")
    assert r.status_code == 200
    grupos = r.get_json()["grupos"]
    assert grupos
    ele = next(g for g in grupos if g["codigo"] == "ELE")
    assert ele["nome"] == "ELETRICO"
    assert ele["total"] >= 1


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