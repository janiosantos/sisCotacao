"""Estados explícitos do resultado fiscal (skill fiscal-mg §11).

Nunca retornar imposto zero silenciosamente por falta de regra: a ausência
deve vir expressa no `status`.
"""
from __future__ import annotations

from enum import Enum


class EstadoFiscal(str, Enum):
    CALCULATED = "CALCULATED"
    RULE_NOT_FOUND = "RULE_NOT_FOUND"
    FISCAL_REVIEW_REQUIRED = "FISCAL_REVIEW_REQUIRED"
    FISCAL_RULE_CONFLICT = "FISCAL_RULE_CONFLICT"
    INVALID_PRODUCT_FISCAL_DATA = "INVALID_PRODUCT_FISCAL_DATA"
    INVALID_OPERATION_CONTEXT = "INVALID_OPERATION_CONTEXT"
    LEGISLATION_OUTDATED = "LEGISLATION_OUTDATED"
    CALCULATION_ERROR = "CALCULATION_ERROR"


# Estados que BLOQUEIAM emissão automática de documento.
BLOQUEADORES = {
    EstadoFiscal.RULE_NOT_FOUND,
    EstadoFiscal.FISCAL_REVIEW_REQUIRED,
    EstadoFiscal.FISCAL_RULE_CONFLICT,
    EstadoFiscal.INVALID_PRODUCT_FISCAL_DATA,
    EstadoFiscal.INVALID_OPERATION_CONTEXT,
    EstadoFiscal.LEGISLATION_OUTDATED,
    EstadoFiscal.CALCULATION_ERROR,
}


def bloqueia_emissao(estado: EstadoFiscal) -> bool:
    return estado in BLOQUEADORES
