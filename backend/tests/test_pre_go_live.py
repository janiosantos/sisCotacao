from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest
from werkzeug.security import generate_password_hash

from catalog_server import pre_go_live
from catalog_server.db import system_conn


def _seed_product_with_image(images_dir: Path) -> tuple[int, Path]:
    with system_conn() as conn:
        category_id = int(
            conn.execute(
                "INSERT INTO categorias (nome,codigo) VALUES (%s,%s) RETURNING id",
                ("Eletrica", "ELE"),
            ).fetchone()["id"]
        )
        subcategory_id = int(
            conn.execute(
                "INSERT INTO subcategorias (categoria_id,nome,codigo) VALUES (%s,%s,%s) RETURNING id",
                (category_id, "Cabos", "CAB"),
            ).fetchone()["id"]
        )
        product_id = int(
            conn.execute(
                "INSERT INTO produtos_cadastro "
                "(nome,marca,sku,ativo,categoria_id,subcategoria_id) "
                "VALUES (%s,%s,%s,1,%s,%s) RETURNING id",
                ("Cabo Flexivel 2,5 mm", "Sil", "ELE-CAB-001", category_id, subcategory_id),
            ).fetchone()["id"]
        )
        relative = f"cadastro/{product_id}/foto principal.jpg"
        conn.execute(
            "INSERT INTO imagens_produto (produto_id,filename,ordem) VALUES (%s,%s,0)",
            (product_id, relative),
        )
    source = images_dir / relative
    source.parent.mkdir(parents=True)
    source.write_bytes(b"imagem-teste-com-conteudo-estavel")
    return product_id, source


def _seed_admin(password: str = "senha-segura-de-go-live") -> int:
    with system_conn() as conn:
        admin_id = int(
            conn.execute(
                "INSERT INTO usuarios (nome,login,senha_hash,ativo) "
                "VALUES (%s,%s,%s,1) RETURNING id",
                ("Administrador", "admin", generate_password_hash(password)),
            ).fetchone()["id"]
        )
        perfil_id = int(
            conn.execute("SELECT id FROM perfis WHERE nome='Administrador'").fetchone()["id"]
        )
        conn.execute(
            "INSERT INTO usuario_perfis (usuario_id,perfil_id) VALUES (%s,%s)",
            (admin_id, perfil_id),
        )
    return admin_id


def test_todas_as_tabelas_possuem_classificacao(system_db):
    with system_conn() as conn:
        tables = set(pre_go_live._public_tables(conn))
    assert tables - pre_go_live.PROTECTED_TABLES - pre_go_live.RESET_TABLES == set()
    assert pre_go_live.PROTECTED_TABLES.isdisjoint(pre_go_live.RESET_TABLES)


def test_exporta_verifica_e_reseta_sem_apagar_cadastros(system_db, tmp_path):
    images_dir = tmp_path / "erp-images"
    gallery_dir = tmp_path / "galeria"
    admin_id = _seed_admin()
    product_id, source = _seed_product_with_image(images_dir)
    with system_conn() as conn:
        conn.execute("INSERT INTO clientes (nome) VALUES (%s)", ("Cliente de teste",))
        conn.execute(
            "INSERT INTO vendedores (nome,comissao_pct) VALUES (%s,%s)",
            ("Vendedor de teste", 3),
        )
        conn.execute(
            "INSERT INTO contas_bancarias "
            "(nome,banco,agencia,conta,digito,saldo_inicial,saldo_atual) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s)",
            ("Conta de teste", "999", "0001", "123", "0", 100, 100),
        )
        conn.execute(
            "INSERT INTO estoque_saldo (deposito_id,produto_id,quantidade) VALUES (1,%s,4)",
            (product_id,),
        )

    exported = pre_go_live.export_images(images_dir, gallery_dir)
    assert exported["source_files"] == 1
    assert exported["exported_files"] == 1
    assert exported["hardlinks"] == 1
    with sqlite3.connect(gallery_dir / "gallery.sqlite3") as conn:
        row = conn.execute(
            "SELECT product_name,category,subcategory,brand,relative_path FROM images"
        ).fetchone()
    assert row[:4] == ("Cabo Flexivel 2,5 mm", "Eletrica", "Cabos", "Sil")
    assert Path(row[4]).name.startswith("ELE_CAB_cabo-flexivel-2-5-mm_sil__P")

    verified = pre_go_live.verify_images(gallery_dir, images_dir)
    assert verified["full_verification"]["error_count"] == 0
    planned = pre_go_live.dry_run(images_dir, gallery_dir)
    assert len(planned["confirmation_token"]) == 64
    assert planned["snapshot"]["reset"]["produtos_cadastro"] == 1

    result = pre_go_live.reset_database(
        images_dir, gallery_dir, planned["confirmation_token"]
    )
    assert result["audit_rows_after"] == 1
    assert not source.exists()
    with sqlite3.connect(gallery_dir / "gallery.sqlite3") as conn:
        relative = conn.execute("SELECT relative_path FROM images").fetchone()[0]
    assert (gallery_dir / "media" / relative).read_bytes() == b"imagem-teste-com-conteudo-estavel"
    with system_conn() as conn:
        assert conn.execute("SELECT COUNT(*) AS n FROM produtos_cadastro").fetchone()["n"] == 0
        assert conn.execute("SELECT COUNT(*) AS n FROM estoque_saldo").fetchone()["n"] == 0
        assert conn.execute("SELECT COUNT(*) AS n FROM vendedores").fetchone()["n"] == 0
        assert conn.execute("SELECT COUNT(*) AS n FROM contas_bancarias").fetchone()["n"] == 0
        clients = conn.execute("SELECT id,nome FROM clientes ORDER BY id").fetchall()
        assert [(row["id"], row["nome"]) for row in clients] == [(1, "CONSUMIDOR")]
        token_version = conn.execute(
            "SELECT token_version FROM usuarios WHERE id=%s", (admin_id,)
        ).fetchone()["token_version"]
        assert token_version == 1


def test_reset_recusa_token_de_outro_snapshot(system_db, tmp_path):
    images_dir = tmp_path / "erp-images"
    gallery_dir = tmp_path / "galeria"
    _seed_admin()
    _seed_product_with_image(images_dir)
    pre_go_live.export_images(images_dir, gallery_dir)
    pre_go_live.verify_images(gallery_dir, images_dir)
    planned = pre_go_live.dry_run(images_dir, gallery_dir)
    with system_conn() as conn:
        conn.execute("INSERT INTO orcamentos (numero,cliente) VALUES (%s,%s)", ("NOVO", "Teste"))
    try:
        pre_go_live.reset_database(images_dir, gallery_dir, planned["confirmation_token"])
    except RuntimeError as exc:
        assert "Token de confirmacao" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("Reset deveria recusar snapshot alterado")


def test_dry_run_recusa_senha_conhecida_do_admin(system_db, tmp_path):
    images_dir = tmp_path / "erp-images"
    gallery_dir = tmp_path / "galeria"
    _seed_product_with_image(images_dir)
    _seed_admin("admin123")
    pre_go_live.export_images(images_dir, gallery_dir)
    pre_go_live.verify_images(gallery_dir, images_dir)

    try:
        pre_go_live.dry_run(images_dir, gallery_dir)
    except RuntimeError as exc:
        assert "senha de teste conhecida" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("Dry-run deveria recusar a credencial admin/admin123")


def test_check_gallery_exige_verificacao_integral(system_db, tmp_path):
    images_dir = tmp_path / "erp-images"
    gallery_dir = tmp_path / "galeria"
    _seed_product_with_image(images_dir)
    pre_go_live.export_images(images_dir, gallery_dir)

    with pytest.raises(RuntimeError, match="verificacao integral"):
        pre_go_live.check_gallery(gallery_dir)

    pre_go_live.verify_images(gallery_dir, images_dir)
    result = pre_go_live.check_gallery(gallery_dir)
    assert result["ready"] is True
    assert result["exported_files"] == 1
    assert result["checked_files"] == 1
    assert result["source_checked_files"] == 1
