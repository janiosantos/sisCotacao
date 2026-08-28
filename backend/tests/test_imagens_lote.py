"""Testes do serviço de imagens em lote (irmaos + dedup de conteúdo)."""
from __future__ import annotations

import shutil

from catalog_server.db import system_conn
from catalog_server.repositories.produtos import ProdutoRepository
from catalog_server.services import imagens_lote
from catalog_server.services import imagens_service

from helpers import criar_familia, produto_dados

repo = ProdutoRepository()


def _criar(familia_id, nome, marca, cor, bitola):
    return repo.create_product(
        familia_id=familia_id, nome=nome, marca=marca,
        descricao=f"{nome} {bitola} {cor} - {marca}", categoria="Eletrica",
        dados=produto_dados(f"SKU-{cor}-{bitola}", "789", preco=1.0),
        atributos={"Cor": cor, "Bitola / Tamanho": bitola},
    )


def test_irmaos_mesma_cor_variando_bitola(system_db):
    fid = criar_familia(repo)
    a = _criar(fid, "Cabo Flexível Teste", "Sil", "preto", "1,5mm²")
    b = _criar(fid, "Cabo Flexível Teste", "Sil", "preto", "2,5mm²")
    c = _criar(fid, "Cabo Flexível Teste", "Sil", "azul", "2,5mm²")  # cor diferente
    d = _criar(fid, "Cabo Flexível Outra Linha", "Sil", "preto", "2,5mm²")  # nome diferente
    with system_conn() as conn:
        ir = imagens_lote.irmaos(conn, a)
    ids = {x["id"] for x in ir}
    assert b in ids       # mesma nome+marca+cor, bitola varia
    assert c not in ids   # cor diferente
    assert d not in ids   # nome diferente


def test_irmaos_sem_cor_agrupa_por_nome_marca(system_db):
    fid = criar_familia(repo)
    a = _criar(fid, "Parafuso Teste", "Ciser", "", "8mm")
    b = _criar(fid, "Parafuso Teste", "Ciser", "", "10mm")
    with system_conn() as conn:
        ir = imagens_lote.irmaos(conn, a)
    ids = {x["id"] for x in ir}
    assert b in ids


def test_conteudo_duplicado_por_md5(system_db):
    pid = _criar(None, "Teste", "X", "preto", "1mm²")
    content = b"fake-image-bytes-123"
    folder = imagens_service._folder(pid)
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "a.jpg").write_bytes(content)
    try:
        assert imagens_service._conteudo_duplicado(pid, content) is True
        assert imagens_service._conteudo_duplicado(pid, b"outro-conteudo") is False
    finally:
        shutil.rmtree(folder, ignore_errors=True)


def test_baixar_lote_limites(system_db):
    res = imagens_lote.baixar_lote(list(range(1, 30)), [], "", None)
    assert res["aplicadas"] == 0
    assert any("20 produtos" in e for e in res["erros"])
    res = imagens_lote.baixar_lote([1], [f"url-{i}" for i in range(25)], "", None)
    assert res["aplicadas"] == 0
    assert any("20 imagens" in e for e in res["erros"])