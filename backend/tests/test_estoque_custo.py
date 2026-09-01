"""Custo médio por depósito e estorno de fatos de estoque (EST-002/003)."""
from __future__ import annotations

from catalog_server.db import system_conn
from catalog_server.repositories import estoque_repo


def _setup(system_db) -> tuple[int, int]:
    with system_conn() as conn:
        conn.execute("INSERT INTO produtos_cadastro (nome, ativo, sku, preco, custo_unitario) VALUES (%s,%s,%s,%s,%s)", ("Prod", 1, "P-1", 10.0, 5.0))
        pid = int(conn.execute("SELECT lastval()").fetchone()["lastval"])
        did = int(conn.execute("SELECT id FROM depositos ORDER BY id LIMIT 1").fetchone()["id"])
        conn.commit()
        return pid, did


def test_entrada_define_custo_medio(system_db):
    pid, did = _setup(system_db)
    r = estoque_repo.movimentar_fato(did, pid, "entrada", 10, custo_unitario=5.0, origem_tipo="teste")
    assert r["custo_medio"] == 5.0
    assert estoque_repo.custo_medio(did, pid) == 5.0


def test_entradas_somam_media_ponderada(system_db):
    pid, did = _setup(system_db)
    estoque_repo.movimentar_fato(did, pid, "entrada", 10, custo_unitario=5.0, origem_tipo="teste")
    estoque_repo.movimentar_fato(did, pid, "entrada", 10, custo_unitario=7.0, origem_tipo="teste")
    # média = (10*5 + 10*7) / 20 = 6.0
    assert estoque_repo.custo_medio(did, pid) == 6.0


def test_saida_usa_custo_do_momento(system_db):
    pid, did = _setup(system_db)
    estoque_repo.movimentar_fato(did, pid, "entrada", 10, custo_unitario=5.0, origem_tipo="teste")
    r = estoque_repo.movimentar_fato(did, pid, "saida", 4, origem_tipo="teste")
    assert r["custo_unitario"] == 5.0  # custo do momento
    assert estoque_repo.custo_medio(did, pid) == 5.0  # saída não muda a média
    assert float(r["saldo_posterior"]) == 6.0


def test_fallback_custo_produto(system_db):
    pid, did = _setup(system_db)  # produto tem custo_unitario=5.0
    r = estoque_repo.movimentar_fato(did, pid, "entrada", 10, origem_tipo="teste")
    assert r["custo_unitario"] == 5.0


def test_estorno_reverte_saldo_e_custo(system_db):
    pid, did = _setup(system_db)
    m1 = estoque_repo.movimentar_fato(did, pid, "entrada", 10, custo_unitario=5.0, origem_tipo="teste")
    estoque_repo.movimentar_fato(did, pid, "entrada", 10, custo_unitario=7.0, origem_tipo="teste")
    assert estoque_repo.custo_medio(did, pid) == 6.0
    # estorna a 2ª entrada (último movimento)
    e = estoque_repo.estornar(did, pid, m1["movimento_id"] + 1, origem_tipo="teste")
    assert e["estornado"] is True
    saldo = estoque_repo.saldo(deposito_id=did, produto_id=pid)[0]
    assert float(saldo["quantidade"]) == 10.0
    assert float(saldo["custo_medio"]) == 5.0
    assert e["tipo"] == "saida"


def test_estorno_idempotente(system_db):
    pid, did = _setup(system_db)
    m = estoque_repo.movimentar_fato(did, pid, "entrada", 10, custo_unitario=5.0, origem_tipo="teste")
    key = "estorno-fixo"
    estoque_repo.estornar(did, pid, m["movimento_id"], idempotency_key=key, origem_tipo="teste")
    r2 = estoque_repo.estornar(did, pid, m["movimento_id"], idempotency_key=key, origem_tipo="teste")
    assert r2["duplicado"] is True
    saldo = estoque_repo.saldo(deposito_id=did, produto_id=pid)[0]
    assert float(saldo["quantidade"]) == 0.0


def test_estorno_ja_estornado_rejeita(system_db):
    pid, did = _setup(system_db)
    m = estoque_repo.movimentar_fato(did, pid, "entrada", 10, custo_unitario=5.0, origem_tipo="teste")
    estoque_repo.estornar(did, pid, m["movimento_id"], origem_tipo="teste")
    try:
        estoque_repo.estornar(did, pid, m["movimento_id"], origem_tipo="teste")
        assert False, "estorno duplo deveria falhar"
    except ValueError:
        pass


def test_estorno_nao_ultimo_rejeita(system_db):
    pid, did = _setup(system_db)
    m1 = estoque_repo.movimentar_fato(did, pid, "entrada", 10, custo_unitario=5.0, origem_tipo="teste")
    estoque_repo.movimentar_fato(did, pid, "entrada", 5, custo_unitario=5.0, origem_tipo="teste")
    try:
        estoque_repo.estornar(did, pid, m1["movimento_id"], origem_tipo="teste")
        assert False, "estorno de movimento não-último deveria falhar (LIFO)"
    except ValueError:
        pass


def test_movimento_tem_origem(system_db):
    pid, did = _setup(system_db)
    r = estoque_repo.movimentar_fato(did, pid, "entrada", 10, custo_unitario=5.0, origem_tipo="compra", origem_id=1, documento="NF-1")
    with system_conn() as conn:
        row = conn.execute(
            "SELECT origem_tipo, origem_id, documento FROM estoque_movimento WHERE id=?",
            (r["movimento_id"],),
        ).fetchone()
    assert row["origem_tipo"] == "compra"
    assert row["origem_id"] == 1
    assert row["documento"] == "NF-1"


def test_saldo_grid_inclui_custo_medio(system_db):
    pid, did = _setup(system_db)
    estoque_repo.movimentar_fato(did, pid, "entrada", 10, custo_unitario=8.0, origem_tipo="teste")
    saldo = estoque_repo.saldo(deposito_id=did, produto_id=pid)[0]
    assert float(saldo["custo_medio"]) == 8.0