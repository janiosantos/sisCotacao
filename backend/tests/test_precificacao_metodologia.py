"""Casos matemáticos da metodologia da planilha de precificação."""
from __future__ import annotations

from catalog_server.services.precificacao_metodologia import calcular


def test_divisor_reproduz_custo_unitario_e_markup_da_planilha():
    result = calcular(
        198,
        embalagem_unitaria=1,
        frete_pct=1,
        cartao_pct=2.5,
        impostos_pct=3,
        despesas_fixas_pct=25,
        margem_pct=15,
    )

    assert result["custo_formacao"] == 199
    assert result["divisor"] == 0.535
    assert result["markup_multiplicador"] == 1.869159
    assert result["preco_sugerido"] == 371.96
    assert result["alertas"] == []


def test_reforma_aplica_ibs_cbs_fora_do_divisor():
    result = calcular(
        100,
        cartao_pct=2.5,
        despesas_fixas_pct=25,
        margem_pct=10,
        cenario_tributario="reforma",
        reforma_tributaria_pct=0.1,
    )

    assert result["preco_sem_tributos"] == 160.0
    assert result["tributos_valor"] == 0.16
    assert result["preco_com_tributos"] == 160.16


def test_divisor_invalido_nao_produz_preco():
    result = calcular(10, margem_pct=100)

    assert result["preco_sugerido"] is None
    assert "menor que 100%" in result["alertas"][0]
