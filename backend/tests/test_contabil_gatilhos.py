"""Gatilhos contábeis configuráveis por evento (v2.15.0, AGENT-produtos P4)."""
from __future__ import annotations

from catalog_server import contabil_gatilhos
from catalog_server.db import system_conn


def _criar_conta(codigo: str, nome: str, tipo: str = "receita") -> int:
    with system_conn() as conn:
        return int(conn.execute(
            "INSERT INTO plano_de_contas (codigo, nome, tipo) VALUES (?,?,?)",
            (codigo, nome, tipo),
        ).lastrowid)


def test_gatilho_inativo_nao_lanca(system_db):
    assert contabil_gatilhos.disparar(
        "venda_autorizada", evento_id=1, valor="100.00"
    ) is False


def test_configurar_ativo_exige_contas(system_db):
    import pytest

    with pytest.raises(ValueError):
        contabil_gatilhos.configurar(
            "venda_autorizada", debito_conta_id=None, credito_conta_id=None, ativo=True
        )


def test_evento_invalido(system_db):
    import pytest

    with pytest.raises(ValueError):
        contabil_gatilhos.configurar(
            "desconhecido", debito_conta_id=1, credito_conta_id=2, ativo=True
        )


def test_gatilho_ativo_lanca_idempotente(system_db):
    deb = _criar_conta("1.01", "Caixa")
    cred = _criar_conta("3.01", "Receita de Venda", "receita")
    contabil_gatilhos.configurar(
        "venda_autorizada",
        debito_conta_id=deb,
        credito_conta_id=cred,
        ativo=True,
        descricao="Venda balcão",
    )

    # Primeira chamada: cria o lançamento
    assert contabil_gatilhos.disparar(
        "venda_autorizada", evento_id=42, valor="150.00",
        historico="Venda 0012", periodo_competencia="2026-08",
        origem_tipo="orcamento",
    ) is True

    # Retrida do mesmo evento: idempotente — `lancar()` devolve False porque o
    # lançamento já existe (o gatilho continua ativo, mas não duplica).
    assert contabil_gatilhos.disparar(
        "venda_autorizada", evento_id=42, valor="150.00",
        historico="Venda 0012", periodo_competencia="2026-08",
        origem_tipo="orcamento",
    ) is False

    with system_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM lancamento_contabil WHERE evento_tipo='venda_autorizada'"
            " AND evento_id=42"
        ).fetchall()
    assert len(rows) == 1
    assert rows[0]["debito_conta_id"] == deb
    assert rows[0]["credito_conta_id"] == cred


def test_ajuste_gatilho_compra_e_venda_lancam_separados(system_db):
    deb = _criar_conta("1.01", "Caixa")
    cred_venda = _criar_conta("3.01", "Receita de Venda", "receita")
    cred_compra = _criar_conta("3.02", "Receita de Compra", "receita")
    contabil_gatilhos.configurar(
        "compra", debito_conta_id=deb, credito_conta_id=cred_compra, ativo=True
    )
    contabil_gatilhos.configurar(
        "ajuste", debito_conta_id=deb, credito_conta_id=cred_venda, ativo=True
    )
    assert contabil_gatilhos.disparar(
        "compra", evento_id=7, valor="50.00", origem_tipo="compra"
    ) is True
    assert contabil_gatilhos.disparar(
        "ajuste", evento_id=8, valor="3.00", origem_tipo="estoque"
    ) is True

    with system_conn() as conn:
        tipos = [r["evento_tipo"] for r in conn.execute(
            "SELECT evento_tipo FROM lancamento_contabil ORDER BY id"
        ).fetchall()]
    assert tipos == ["compra", "ajuste"]


def test_desativar_gatilho_para_de_lancar(system_db):
    deb = _criar_conta("1.01", "Caixa")
    cred = _criar_conta("3.01", "Receita de Venda", "receita")
    contabil_gatilhos.configurar(
        "venda_autorizada", debito_conta_id=deb, credito_conta_id=cred, ativo=False
    )
    assert contabil_gatilhos.disparar(
        "venda_autorizada", evento_id=99, valor="10.00"
    ) is False