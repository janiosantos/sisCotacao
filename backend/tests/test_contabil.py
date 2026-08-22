"""Pré-lançamentos contábeis: idempotência por evento."""
from __future__ import annotations

from catalog_server.contabil import lancar


def test_lancamento_idempotente():
    key = "venda-999999-teste"
    assert lancar(
        evento_tipo="venda", evento_id=999999,
        idempotency_key=key,
        debito_conta_id=None, credito_conta_id=None,
        valor="150.00", historico="teste", periodo_competencia="2026-08",
        origem_tipo="orcamento",
    ) is True
    # Retrida do mesmo evento ignora:
    assert lancar(
        evento_tipo="venda", evento_id=999999,
        idempotency_key=key,
        debito_conta_id=None, credito_conta_id=None,
        valor="150.00",
    ) is False
