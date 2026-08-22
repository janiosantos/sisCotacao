"""Golden tests das engines fiscais — números FICTÍCIOS de engenharia.

Nenhuma alíquota aqui é parâmetro legal: entra como INPUT da regra.
Cenários estruturais do §23 (Simples primeiro) + matemática do kit §5-6.
"""
from __future__ import annotations

from decimal import Decimal

from catalog_server.fiscal.engines import (
    difal_entrada,
    difal_saida,
    icms_proprio,
    icms_st,
)


def test_icms_proprio_sem_reducao():
    r = icms_proprio(Decimal("1000.00"), Decimal("18"))
    assert r["base"] == Decimal("1000.00")
    assert r["valor"] == Decimal("180.00")


def test_icms_proprio_com_reducao():
    # redução 20% -> base 800; 18% -> 144
    r = icms_proprio(Decimal("1000.00"), Decimal("18"), Decimal("20"))
    assert r["base"] == Decimal("800.00")
    assert r["valor"] == Decimal("144.00")


def test_simples_venda_interna_102_sem_icms_proprio():
    """CSOSN 102: tributação fica no DAS — engine não gera ICMS próprio."""
    r = icms_proprio(Decimal("1000.00"), Decimal("0"))
    assert r["valor"] == Decimal("0.00")


def test_substituido_ja_retida_nao_invoca_st():
    """CST 060/CSOSN 500 (mercadoria já retida): decisão da REGRA — a engine
    de ST nem é invocada e o ICMS próprio é zero."""
    r = icms_proprio(Decimal("1000.00"), Decimal("0"))
    assert r["valor"] == Decimal("0.00")


def test_st_mva_original_calculo():
    # operação 1000 + MVA 40% = base 1400; interna 18% = 252;
    # ICMS próprio (inter 7%) = 70 -> ST = 252 - 70 = 182
    st = icms_st(
        Decimal("1000.00"),
        metodo="mva_original",
        mva_pct=Decimal("40"),
        icms_inter=Decimal("70"),
        aliquota_interna=Decimal("18"),
    )
    assert st["icms_st_base"] == Decimal("1400.00")
    assert st["icms_proprio"] == Decimal("70")
    assert st["icms_st_value"] == Decimal("182.00")


def test_st_preco_fixado_com_componentes():
    st = icms_st(
        Decimal("1000.00"),
        metodo="preco_fixado",
        preco_fixado=Decimal("1500.00"),
        ipi=Decimal("50"),
        frete=Decimal("30"),
        icms_inter=Decimal("90"),
        aliquota_interna=Decimal("18"),
    )
    # base 1580; 18% = 284,40; próprio 90 -> ST 194,40
    assert st["icms_st_base"] == Decimal("1580.00")
    assert st["icms_st_value"] == Decimal("194.40")


def test_st_metodo_desconhecido_erro():
    import pytest

    with pytest.raises(ValueError):
        icms_st(Decimal("100"), metodo="inventado", aliquota_interna=Decimal("18"))


def test_difal_entrada_por_dentro_kit():
    """Fórmula §6 do kit com inputs arbitrários:
    vo=1000, icms_origem=70, interna=18 ->
    base = (1000-70)/(1-0.18) = 1134.1463... -> 1134.15
    difal = 1134.15*0.18 - 70 = 134.15 (arredondado)
    """
    r = difal_entrada(Decimal("1000.00"), Decimal("70"), Decimal("18"), por_dentro=True)
    assert r["base_destino"] == Decimal("1134.15")
    assert r["difal_value"] == Decimal("134.15")


def test_difal_entrada_sem_por_dentro():
    r = difal_entrada(Decimal("1000.00"), Decimal("70"), Decimal("18"), por_dentro=False)
    assert r["base_destino"] == Decimal("1000.00")
    assert r["difal_value"] == Decimal("110.00")


def test_difal_saida_consumidor_final_com_fcp():
    # base 1000; inter 7% = 70; interna 18% - fcp 2% => difal base 1600? não:
    # difal_base = 1000*(18-2)/100 = 160; difal = 160-70 = 90; fcp = 20
    r = difal_saida(
        Decimal("1000.00"),
        Decimal("7"),
        Decimal("18"),
        fcp_rate=Decimal("2"),
    )
    assert r["difal_base"] == Decimal("160.00")
    assert r["difal_value"] == Decimal("90.00")
    assert r["fcp_value"] == Decimal("20.00")
