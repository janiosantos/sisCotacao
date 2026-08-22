"""Política de precisão fiscal (skill fiscal-mg §15).

- Dinheiro: 2 casas, ROUND_HALF_UP.
- Alíquotas/pct: 4 casas, ROUND_HALF_UP.
- Nunca float para dinheiro ou tributo; conversões aceitam str/int/float
  de origens externas e convergem para Decimal imediatamente.
"""
from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

Q_DINHEIRO = Decimal("0.01")
Q_ALIQUOTA = Decimal("0.0001")


def to_decimal(valor) -> Decimal | None:
    """Converte str/int/float/Decimal para Decimal (None/'' -> None)."""
    if valor is None or valor == "":
        return None
    if isinstance(valor, Decimal):
        return valor
    try:
        return Decimal(str(valor))
    except (InvalidOperation, ValueError, TypeError):
        return None


def dinheiro(valor) -> Decimal:
    d = to_decimal(valor) or Decimal("0")
    return d.quantize(Q_DINHEIRO, rounding=ROUND_HALF_UP)


def aliquota(valor) -> Decimal:
    d = to_decimal(valor) or Decimal("0")
    return d.quantize(Q_ALIQUOTA, rounding=ROUND_HALF_UP)
