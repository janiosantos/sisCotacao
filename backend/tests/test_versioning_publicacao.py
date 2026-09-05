from catalog_server import versioning


def test_componentes_todos_cobre_deployment_sem_publicar_site_externo(monkeypatch):
    manifestos = [
        {
            "versao": "v2.40.0",
            "componentes": ["backend", "frontend", "deployment"],
        },
        {
            "versao": "v2.35.0",
            "componentes": ["backend", "deployment", "site-institucional"],
        },
    ]
    registrados = []

    monkeypatch.setattr(versioning, "listar_manifestos_pendentes", lambda: manifestos)
    monkeypatch.setattr(versioning, "_schema_version", lambda: 156)
    monkeypatch.setattr(
        versioning,
        "_registrar_log",
        lambda **dados: registrados.append(dados["versao_release"]),
    )

    publicadas = versioning.registrar_publicacao(versioning._COMPONENTES_TODOS)

    assert publicadas == ["v2.40.0"]
    assert registrados == ["v2.40.0"]


def test_publicacao_filtra_exatamente_a_versao_promovida(monkeypatch):
    manifestos = [
        {"versao": "v2.39.1", "componentes": ["backend"]},
        {"versao": "v2.40.1", "componentes": ["backend", "frontend", "deployment"]},
        {"versao": "v2.41.0", "componentes": ["frontend"]},
    ]
    registrados = []

    monkeypatch.setattr(versioning, "listar_manifestos_pendentes", lambda: manifestos)
    monkeypatch.setattr(versioning, "_schema_version", lambda: 156)
    monkeypatch.setattr(
        versioning,
        "_registrar_log",
        lambda **dados: registrados.append(dados["versao_release"]),
    )

    publicadas = versioning.registrar_publicacao(
        versioning._COMPONENTES_TODOS,
        versao="v2.40.1",
    )

    assert publicadas == ["v2.40.1"]
    assert registrados == ["v2.40.1"]
