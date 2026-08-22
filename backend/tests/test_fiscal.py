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

from helpers import attrs, criar_familia, variante

repo = ProdutoRepository()


@pytest.fixture()
def variante_id(system_db):
    fid = criar_familia(repo, ncm_padrao="85444900")
    aid = {a["nome"]: str(a["id"]) for a in repo.get_familia(fid)["atributos"]}
    pid = repo.create_product(
        familia_id=fid,
        nome="Cabo Flexível Sil",
        marca="Sil",
        descricao="",
        categoria="Eletrica",
        variantes=[variante("SKU-FISCAL", "7894001", attrs(aid, Bitola="2,5mm"), preco=10.0)],
    )
    with system_conn() as conn:
        return conn.execute(
            "SELECT id FROM variantes WHERE sku='SKU-FISCAL'"
        ).fetchone()[0]


def test_sync_ncm_cria_fiscal_config(variante_id):
    cfg = fiscal_config_repo.get(variante_id)
    assert cfg is not None
    assert cfg["ncm"] == "85444900"  # herdado da família
    assert cfg["variante_id"] == variante_id


def test_fiscal_config_upsert_eh_1para1(variante_id):
    fiscal_config_repo.upsert(
        variante_id,
        ncm="85444900",
        cfop="5.102",
        cst_icms="00",
        aliquota_icms=18.0,
    )
    cfg = fiscal_config_repo.get(variante_id)
    assert cfg["cfop"] == "5.102"
    assert cfg["cst_icms"] == "00"
    assert cfg["aliquota_icms"] == 18.0
    with system_conn() as conn:
        n = conn.execute(
            "SELECT COUNT(*) FROM fiscal_config WHERE variante_id=?", (variante_id,)
        ).fetchone()[0]
    assert n == 1  # upsert não duplica a linha


def test_registrar_historico_config(variante_id):
    hid = fiscal_config_repo.registrar_historico_config(variante_id, "atualizado")
    assert hid > 0
    hist = fiscal_config_repo.list_historico(variante_id=variante_id)
    assert len(hist) == 1
    assert hist[0]["tipo"] == "atualizado"
    assert hist[0]["ncm"] == "85444900"


def test_gerar_config_padrao(variante_id):
    # já existe config do _sync_ncm; gerar deve ignorar (1:1 preservado)
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