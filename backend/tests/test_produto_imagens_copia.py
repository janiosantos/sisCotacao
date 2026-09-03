"""Cópia de imagens ao duplicar produto (endpoint + serviço)."""
from __future__ import annotations

import catalog_server.services.imagens_service as img_svc
from catalog_server.db import system_conn
from catalog_server.repositories import produto_repo


def _criar(nome: str) -> int:
    return produto_repo.create_product(
        None, nome, "", "", "", "", "", None, None, None, {}, {}
    )


def _imagens(produto_id: int) -> list[dict]:
    with system_conn() as conn:
        rows = conn.execute(
            "SELECT filename, ordem FROM imagens_produto WHERE produto_id=? ORDER BY ordem, id",
            (produto_id,),
        ).fetchall()
        return [dict(r) for r in rows]


def test_copiar_imagens_duplica_arquivos_e_registros(system_db, tmp_path, monkeypatch):
    monkeypatch.setattr(img_svc, "IMAGES_DIR", tmp_path)
    origem = _criar("Origem")
    destino = _criar("Destino")

    src = tmp_path / "cadastro" / str(origem)
    src.mkdir(parents=True)
    (src / "foto1.jpg").write_bytes(b"AAA")
    (src / "foto2.jpg").write_bytes(b"BBB")
    produto_repo.add_imagem(origem, f"cadastro/{origem}/foto1.jpg")
    produto_repo.add_imagem(origem, f"cadastro/{origem}/foto2.jpg")

    copiadas = img_svc.copiar_imagens(origem, destino, produto_repo)
    assert len(copiadas) == 2

    dst = tmp_path / "cadastro" / str(destino)
    arquivos = sorted(p.name for p in dst.iterdir())
    assert len(arquivos) == 2
    assert all(n.startswith("copia_") for n in arquivos)

    regs = _imagens(destino)
    assert len(regs) == 2
    assert regs[0]["ordem"] == 0  # capa preservada na primeira
    assert regs[0]["filename"] != regs[1]["filename"]


def test_copiar_imagens_sem_origem_nao_duplica(system_db, tmp_path, monkeypatch):
    monkeypatch.setattr(img_svc, "IMAGES_DIR", tmp_path)
    destino = _criar("Destino")
    assert img_svc.copiar_imagens(999999, destino, produto_repo) == []
    assert _imagens(destino) == []


def test_api_copiar_imagens(system_db, tmp_path, monkeypatch):
    monkeypatch.setattr(img_svc, "IMAGES_DIR", tmp_path)
    from catalog_server import auth_token, permissao
    from catalog_server.app_factory import create_app
    from werkzeug.security import generate_password_hash

    with system_conn() as conn:
        cur = conn.execute(
            "INSERT INTO usuarios (nome, login, senha_hash) VALUES (%s,%s,%s)",
            ("Adm", "admimg", generate_password_hash("x123")),
        )
        uid = int(cur.lastrowid)
        perfil = conn.execute("SELECT id FROM perfis WHERE nome=%s", ("Administrador",)).fetchone()["id"]
        conn.execute(
            "INSERT INTO usuario_perfis (usuario_id, perfil_id) VALUES (%s,%s) ON CONFLICT DO NOTHING",
            (uid, perfil),
        )
        conn.commit()
    permissao.invalidar(uid)
    token = {"Authorization": f"Bearer {auth_token.criar_token({'id': uid, 'login': 'admimg'})}"}

    origem = _criar("Origem")
    destino = _criar("Destino")
    src = tmp_path / "cadastro" / str(origem)
    src.mkdir(parents=True)
    (src / "foto.jpg").write_bytes(b"IMG")
    produto_repo.add_imagem(origem, f"cadastro/{origem}/foto.jpg")

    client = create_app().test_client()
    r = client.post(f"/api/produtos-cadastro/{destino}/imagens/copiar", headers=token, json={"de": origem})
    assert r.status_code == 201
    body = r.get_json()
    assert body["copiadas"] == 1
    assert len(body["imagens"]) == 1
    assert _imagens(destino)

    # origem inexistente -> 404
    r = client.post(f"/api/produtos-cadastro/{destino}/imagens/copiar", headers=token, json={"de": 999999})
    assert r.status_code == 404