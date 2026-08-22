"""FiscalContext — contexto da operação (skill fiscal-mg §10).

Campos monetários chegam como Decimal (conversão via de_dict).
Adicionar campos somente quando uma regra exigir.
"""
from __future__ import annotations

from dataclasses import dataclass, field, fields
from decimal import Decimal

from catalog_server.fiscal.decimais import to_decimal

_MONETARIOS = {
    "quantity",
    "unit_price",
    "discount",
    "freight",
    "insurance",
    "other_expenses",
    "ipi",
}


@dataclass
class FiscalContext:
    company_id: int | None = None
    establishment_id: int | None = None
    tax_regime: str = ""
    ie: str = ""
    uf_origin: str = ""
    uf_destination: str = ""
    operation_type: str = ""
    operation_date: str = ""
    customer_type: str = ""
    customer_taxpayer_status: str = ""
    final_consumer: bool | None = None
    merchandise_purpose: str = ""
    stock_origin: str = ""
    document_model: str = ""  # 55 NF-e / 65 NFC-e
    document_series: str = ""
    product_id: int | None = None
    ncm: str = ""
    cest: str = ""
    merchandise_origin: str = ""
    quantity: Decimal | None = None
    unit_price: Decimal | None = None
    discount: Decimal | None = None
    freight: Decimal | None = None
    insurance: Decimal | None = None
    other_expenses: Decimal | None = None
    ipi: Decimal | None = None
    original_document_id: int | None = None
    extras: dict = field(default_factory=dict)

    @classmethod
    def de_dict(cls, dados: dict) -> "FiscalContext":
        """Constrói o contexto a partir de um dict arbitrário, convertendo
        campos monetários para Decimal e ignorando desconhecidos (extras)."""
        conhecidos = {f.name for f in fields(cls)}
        kwargs: dict = {}
        extras = {}
        for k, v in (dados or {}).items():
            if k not in conhecidos:
                if v not in (None, ""):
                    extras[k] = v
                continue
            if k in _MONETARIOS:
                v = to_decimal(v)
            kwargs[k] = v
        ctx = cls(**kwargs)
        ctx.extras = extras
        return ctx
