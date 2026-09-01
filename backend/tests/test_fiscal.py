"""Testes de regressão do módulo fiscal (fiscal_config, CFOP/CST, histórico)."""
from __future__ import annotations

import pytest

from catalog_server.db import system_conn
from catalog_server.repositories.fiscal import (
    cest_repo,
    cfop_repo,
    csosn_repo,
    cst_repo,
    fiscal_config_repo,
)
from catalog_server.repositories.produtos import ProdutoRepository

from helpers import criar_familia

repo = ProdutoRepository()


@pytest.fixture()
def produto_id(system_db):
    fid = criar_familia(repo, ncm_padrao="85444900")
    pid = repo.create_product(
        familia_id=fid,
        nome="Cabo Flexível Sil",
        marca="Sil",
        descricao="",
        categoria="Eletrica",
        dados={"sku": "SKU-FISCAL", "ean": "7894001", "preco": 10.0, "ncm": "85444900"},
        atributos={"Bitola": "2,5mm"},
    )
    # O antigo _sync_ncm criava a fiscal_config no create_product; agora é
    # criada explicitamente para os testes de histórico/1:1 abaixo.
    fiscal_config_repo.upsert(pid, ncm="85444900")
    return pid


def test_fiscal_config_upsert_eh_1para1(produto_id):
    fiscal_config_repo.upsert(
        produto_id,
        ncm="85444900",
        cfop="5.102",
        cst_icms="00",
        aliquota_icms=18.0,
    )
    cfg = fiscal_config_repo.get(produto_id)
    assert cfg["cfop"] == "5.102"
    assert cfg["cst_icms"] == "00"
    assert cfg["aliquota_icms"] == 18.0
    with system_conn() as conn:
        n = conn.execute(
            "SELECT COUNT(*) FROM fiscal_config WHERE produto_id=?", (produto_id,)
        ).fetchone()[0]
    assert n == 1  # upsert não duplica a linha


def test_registrar_historico_config(produto_id):
    hid = fiscal_config_repo.registrar_historico_config(produto_id, "atualizado")
    assert hid > 0
    hist = fiscal_config_repo.list_historico(produto_id=produto_id)
    assert len(hist) == 1
    assert hist[0]["tipo"] == "atualizado"
    assert hist[0]["ncm"] == "85444900"


def test_gerar_config_padrao(produto_id):
    # já existe config criada no fixture; gerar deve ignorar (1:1 preservado)
    count = fiscal_config_repo.gerar_config_padrao()
    assert count == 0
    with system_conn() as conn:
        n = conn.execute("SELECT COUNT(*) FROM fiscal_config").fetchone()[0]
    assert n == 1


def test_cfop_cst_list():
    cfops = cfop_repo.list()
    assert isinstance(cfops, list)
    icms = cst_repo.list("cst_icms")
    assert len(icms) >= 1
    pis = cst_repo.list("cst_pis")
    assert len(pis) >= 1


def test_cest_csosn_list():
    cests = cest_repo.list()
    assert isinstance(cests, list)
    csosns = csosn_repo.list()
    assert isinstance(csosns, list)