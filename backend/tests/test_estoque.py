"""Testes de regressão do estoque (saldo, movimentações, transferência, lotes)."""
from __future__ import annotations

import pytest

from catalog_server.db import system_conn
from catalog_server.repositories.estoque import estoque_repo, lote_repo
from catalog_server.repositories.produtos import ProdutoRepository

from helpers import criar_familia, produto_dados

repo = ProdutoRepository()

DEPOSITO = 1


@pytest.fixture()
def deposito_2(system_db):
    with system_conn() as conn:
        cur = conn.execute(
            "INSERT INTO depositos (nome, ativo, criado_em) VALUES ('Filial', 1, datetime('now'))"
        )
        return cur.lastrowid


@pytest.fixture()
def variante_id(system_db):
    fid = criar_familia(repo)
    pid = repo.create_product(
        familia_id=fid,
        nome="Cabo Flexível Sil",
        marca="Sil",
        descricao="",
        categoria="Eletrica",
        dados=produto_dados("SKU-EST", "7892001", preco=10.0),
        atributos={"Bitola": "2,5mm"},
    )
    return pid


def _saldo(variante_id):
    with system_conn() as conn:
        row = conn.execute(
            "SELECT quantidade FROM estoque_saldo WHERE deposito_id=? AND produto_id=?",
            (DEPOSITO, variante_id),
        ).fetchone()
    return row["quantidade"] if row else None


def test_saldo_inicial_zero(variante_id):
    # cria a linha de saldo (0) com um movimento neutro
    estoque_repo.movimentar(DEPOSITO, variante_id, "entrada", 0, documento="TST-0")
    saldo = estoque_repo.saldo(deposito_id=DEPOSITO, variante_id=variante_id)
    assert len(saldo) == 1
    assert saldo[0]["quantidade"] == 0
    assert saldo[0]["sku"] == "SKU-EST"
    assert saldo[0]["situacao"] == "ok"


def test_movimentar_entrada(variante_id):
    res = estoque_repo.movimentar(DEPOSITO, variante_id, "entrada", 10, documento="TST-1")
    assert res["saldo_anterior"] == 0
    assert res["saldo_posterior"] == 10
    assert _saldo(variante_id) == 10
    movs = estoque_repo.movimentos(deposito_id=DEPOSITO, variante_id=variante_id)
    assert len(movs) == 1
    assert movs[0]["tipo"] == "entrada"
    assert movs[0]["quantidade"] == 10
    assert movs[0]["saldo_posterior"] == 10


def test_movimentar_saida_nao_negativa(variante_id):
    estoque_repo.movimentar(DEPOSITO, variante_id, "entrada", 5)
    res = estoque_repo.movimentar(DEPOSITO, variante_id, "saida", 3)
    assert res["saldo_posterior"] == 2
    res2 = estoque_repo.movimentar(DEPOSITO, variante_id, "saida", 99)
    assert res2["saldo_posterior"] == 0


def test_movimentar_ajuste(variante_id):
    estoque_repo.movimentar(DEPOSITO, variante_id, "entrada", 5)
    res = estoque_repo.movimentar(DEPOSITO, variante_id, "ajuste", 7)
    assert res["saldo_posterior"] == 7
    res2 = estoque_repo.movimentar(DEPOSITO, variante_id, "ajuste", 0)
    assert res2["saldo_posterior"] == 0


def test_transferir_entre_depositos(variante_id, deposito_2):
    estoque_repo.movimentar(DEPOSITO, variante_id, "entrada", 8)
    res = estoque_repo.transferir(DEPOSITO, deposito_2, variante_id, 3)
    assert res["ok"]
    assert _saldo(variante_id) == 5
    with system_conn() as conn:
        destino = conn.execute(
            "SELECT quantidade FROM estoque_saldo WHERE deposito_id=? AND produto_id=?",
            (deposito_2, variante_id),
        ).fetchone()["quantidade"]
    assert destino == 3


def test_lotes_create_list(variante_id):
    lote_id = lote_repo.create(
        DEPOSITO, variante_id, "LOT-1", quantidade=10,
        data_fabricacao="2026-01-01", data_validade="2026-12-31",
    )
    assert lote_id > 0
    lote = lote_repo.get(lote_id)
    assert lote["codigo"] == "LOT-1"
    assert lote["quantidade"] == 10
    lotes = lote_repo.list(deposito_id=DEPOSITO, variante_id=variante_id)
    assert len(lotes) == 1
    assert lotes[0]["produto_nome"] == "Cabo Flexível Sil"