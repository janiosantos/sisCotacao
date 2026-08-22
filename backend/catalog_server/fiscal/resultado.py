"""FiscalResult — resultado estruturado e explicável (skill fiscal-mg §11).

Valores monetários/alíquotas em Decimal; `para_dict()` serializa para JSON
(Decimal -> str) preservando o status explicável.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal

from catalog_server.fiscal.estados import EstadoFiscal


def _serializavel(v):
    if isinstance(v, Decimal):
        return str(v)
    return v


@dataclass
class FiscalResult:
    status: EstadoFiscal = EstadoFiscal.CALCULATED
    cfop: str | None = None
    cst: str | None = None
    csosn: str | None = None
    icms_base: Decimal | None = None
    icms_rate: Decimal | None = None
    icms_value: Decimal | None = None
    icms_st_base: Decimal | None = None
    icms_st_rate: Decimal | None = None
    icms_st_value: Decimal | None = None
    difal_base: Decimal | None = None
    difal_rate: Decimal | None = None
    difal_value: Decimal | None = None
    fcp_base: Decimal | None = None
    fcp_rate: Decimal | None = None
    fcp_value: Decimal | None = None
    rule_id: int | str | None = None
    rule_version: int | str | None = None
    legal_reference: str | None = None
    source_url: str | None = None
    matched_conditions: list = field(default_factory=list)
    warnings: list = field(default_factory=list)
    errors: list = field(default_factory=list)

    def bloqueia_emissao(self) -> bool:
        from catalog_server.fiscal.estados import BLOQUEADORES

        return self.status in BLOQUEADORES

    def para_dict(self) -> dict:
        out: dict = {}
        for k, v in self.__dict__.items():
            if k == "status":
                out[k] = v.value if isinstance(v, EstadoFiscal) else v
            elif isinstance(v, list):
                out[k] = [_serializavel(i) for i in v]
            else:
                out[k] = _serializavel(v)
        return out

    @classmethod
    def revisao(cls, motivo: str, **ctx) -> "FiscalResult":
        """Atalho para FISCAL_REVIEW_REQUIRED com o porquê registrado."""
        return cls(status=EstadoFiscal.FISCAL_REVIEW_REQUIRED, errors=[motivo], **ctx)
