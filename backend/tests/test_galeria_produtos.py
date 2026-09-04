from __future__ import annotations

import hashlib

from catalog_server.db import system_conn
from catalog_server.repositories import produto_repo
from catalog_server.services import galeria_service, imagens_service


def _product() -> int:
    with system_conn() as conn:
        return int(
            conn.execute(
                "INSERT INTO produtos_cadastro (nome,sku,ativo) VALUES (%s,%s,1) RETURNING id",
                ("Produto galeria", "GAL-001"),
            ).fetchone()["id"]
        )


def test_importacao_da_galeria_e_atomica_e_deduplica(system_db, tmp_path, monkeypatch):
    product_id = _product()
    content = b"conteudo-da-imagem"
    digest = hashlib.sha256(content).hexdigest()
    monkeypatch.setattr(imagens_service, "IMAGES_DIR", tmp_path)
    monkeypatch.setattr(
        galeria_service,
        "_download",
        lambda image_id: (content, ".jpg", digest),
    )

    first = galeria_service.importar(product_id, [10, 10], produto_repo)
    assert len(first["saved"]) == 1
    assert first["deduplicated"] == 0
    assert (tmp_path / first["saved"][0]).is_file()
    with system_conn() as conn:
        rows = conn.execute(
            "SELECT filename,ordem FROM imagens_produto WHERE produto_id=%s",
            (product_id,),
        ).fetchall()
    assert len(rows) == 1
    assert rows[0]["ordem"] == 0

    second = galeria_service.importar(product_id, [11], produto_repo)
    assert second == {"saved": [], "deduplicated": 1}


def test_importacao_limita_quantidade_antes_de_baixar(system_db, monkeypatch):
    product_id = _product()
    called = False

    def download(_image_id):
        nonlocal called
        called = True
        raise AssertionError

    monkeypatch.setattr(galeria_service, "_download", download)
    try:
        galeria_service.importar(
            product_id, list(range(1, galeria_service.MAX_SELECTION + 2)), produto_repo
        )
    except ValueError as exc:
        assert "maximo" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("Limite deveria ser aplicado")
    assert called is False


def test_validacao_de_assinaturas_de_imagem():
    assert galeria_service._valid_image_content("image/bmp", b"BM" + b"\0" * 12)
    assert galeria_service._valid_image_content(
        "image/avif", b"\0\0\0\x18ftypavif\0\0\0\0"
    )
    assert not galeria_service._valid_image_content("image/jpeg", b"arquivo-falso")
    assert not galeria_service._valid_image_content("text/html", b"<html></html>")
