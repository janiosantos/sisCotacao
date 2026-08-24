"""Provedor Sicoob — boleto e PIX (FASE 2, reservado).

Implementação prevista para a fase 2 (requer certificado ICP-Brasil PFX,
OAuth2 client credentials e client_id). Enquanto não implementado, os
métodos lançam erro claro para não serem usados por engano.
"""
from __future__ import annotations

from catalog_server.payments.base import PaymentProvider


class SicoobProvider(PaymentProvider):
    codigo = "sicoob"
    nome = "Sicoob"

    def _nao_implementado(self):
        raise NotImplementedError(
            "Sicoob está previsto para a fase 2 (exige certificado digital). "
            "Use Asaas ou Mercado Pago para emissão."
        )

    def emitir_boleto(self, conta: dict, emitente: dict) -> dict:
        self._nao_implementado()

    def emitir_pix(self, conta: dict) -> dict:
        self._nao_implementado()

    def consultar(self, payment_id: str) -> dict:
        self._nao_implementado()

    def webhook(self, payload: dict, headers: dict) -> dict | None:
        return None