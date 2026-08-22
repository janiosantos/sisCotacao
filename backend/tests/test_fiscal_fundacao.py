"""Fundação do domínio fiscal: estados, contexto, resultado e política Decimal."""
from __future__ import annotations

from decimal import Decimal

from catalog_server.fiscal import FiscalContext, FiscalResult, EstadoFiscal
from catalog_server.fiscal.decimais import aliquota, dinheiro, to_decimal


def test_estados_cobrem_spec():
    esperados = {
        "CALCULATED",
        "RULE_NOT_FOUND",
        "FISCAL_REVIEW_REQUIRED",
        "FISCAL_RULE_CONFLICT",
        "INVALID_PRODUCT_FISCAL_DATA",
        "INVALID_OPERATION_CONTEXT",
        "LEGISLATION_OUTDATED",
        "CALCULATION_ERROR",
    }
    assert {e.value for e in EstadoFiscal} == esperados


def test_bloqueadores_impedem_emissao():
    from catalog_server.fiscal.estados import bloqueia_emissao

    assert not bloqueia_emissao(EstadoFiscal.CALCULATED)
    assert bloqueia_emissao(EstadoFiscal.RULE_NOT_FOUND)
    assert bloqueia_emissao(EstadoFiscal.FISCAL_REVIEW_REQUIRED)
    r = FiscalResult(status=EstadoFiscal.FISCAL_RULE_CONFLICT)
    assert r.bloqueia_emissao()


def test_contexto_de_dict_converte_monetarios():
    ctx = FiscalContext.de_dict(
        {
            "tax_regime": "simples_nacional",
            "uf_origin": "MG",
            "uf_destination": "SP",
            "operation_date": "2026-08-22",
            "quantity": "10.5",
            "unit_price": 12.34,
            "discount": None,
            "campo_desconhecido": "vai para extras",
        }
    )
    assert ctx.tax_regime == "simples_nacional"
    assert ctx.quantity == Decimal("10.5")
    assert ctx.unit_price == Decimal("12.34")
    assert ctx.discount is None
    assert ctx.extras == {"campo_desconhecido": "vai para extras"}


def test_resultado_para_dict_serializa_decimal_e_status():
    r = FiscalResult(
        cfop="5102",
        csosn="102",
        icms_base=Decimal("100.00"),
        icms_rate=Decimal("0.1800"),
        rule_id=7,
    )
    d = r.para_dict()
    assert d["status"] == "CALCULATED"
    assert d["icms_base"] == "100.00"
    assert isinstance(d["icms_base"], str)
    assert d["cfop"] == "5102"


def test_revisao_atalho_review_required():
    r = FiscalResult.revisao("MVA sem fonte oficial", cfop="5405")
    assert r.status is EstadoFiscal.FISCAL_REVIEW_REQUIRED
    assert r.errors == ["MVA sem fonte oficial"]
    assert r.bloqueia_emissao()


def test_politica_decimais_half_up():
    assert dinheiro("10.005") == Decimal("10.01")  # half-up, não banker's
    assert dinheiro(None) == Decimal("0.00")
    assert aliquota("18") == Decimal("18.0000")
    assert to_decimal("") is None
    assert to_decimal("abc") is None
