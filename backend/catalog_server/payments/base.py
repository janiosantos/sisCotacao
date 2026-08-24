"""Interface dos provedores de pagamento (boleto/PIX) das contas a receber.

Cada provedor (Asaas, Mercado Pago, EfiPay, Sicoob) implementa esta interface.
O `registry` escolhe o provedor pela prioridade de custo configurada por
operação (boleto/pix), permitindo troca sem mudança de código.
"""
from __future__ import annotations

from abc import ABC, abstractmethod


class PaymentProvider(ABC):
    """Contrato mínimo para emissão de boleto/PIX e webhook."""

    codigo: str = ""
    nome: str = ""

    def __init__(self, cfg: dict):
        self.cfg = cfg  # linha de payment_provider_config

    # -- Emissão ----------------------------------------------------------

    @abstractmethod
    def emitir_boleto(self, conta: dict, emitente: dict) -> dict:
        """Gera um boleto para a conta a receber.

        Retorna dict normalizado:
          {payment_id, status_cobranca, linha_digitavel, codigo_barras,
           nosso_numero, url_boleto, webhook_id?}
        """

    @abstractmethod
    def emitir_pix(self, conta: dict) -> dict:
        """Gera uma cobrança PIX (QR code + copia-e-cola) para a conta.

        Retorna dict normalizado:
          {payment_id, status_cobranca, payload_pix, qr_code_base64,
           txid, url_pix?}
        """

    # -- Consulta / cancelamento -------------------------------------------

    @abstractmethod
    def consultar(self, payment_id: str) -> dict:
        """Consulta o status atual de uma cobrança na plataforma.

        Retorna {status_cobranca, ...dados}
        (status_cobranca: 'pendente' | 'pago' | 'cancelado' | 'erro').
        """

    def cancelar(self, payment_id: str) -> dict:
        """Cancela uma cobrança (opcional; default sem ação)."""
        return {"ok": True}

    # -- Webhook -----------------------------------------------------------

    @abstractmethod
    def webhook(self, payload: dict, headers: dict) -> dict | None:
        """Valida e normaliza o evento recebido da plataforma.

        Devolve dict normalizado:
          {payment_id, status_cobranca, webhook_id?, valor?}
        ou None se o evento não for de pagamento confirmado / for inválido.
        """