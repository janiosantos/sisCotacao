"""Interface dos provedores de pagamento (boleto/PIX) das contas a receber.

Cada provedor (Asaas, Mercado Pago, EfiPay, Sicoob) implementa esta interface.
O `registry` escolhe o provedor pela prioridade de custo configurada por
operação (boleto/pix), permitindo troca sem mudança de código.
"""
from __future__ import annotations

import hmac
import os
from abc import ABC, abstractmethod


class WebhookNaoAutorizado(ValueError):
    """Assinatura/token do webhook inválido, ausente ou expirado."""


def const_time_equal(a: str, b: str) -> bool:
    return hmac.compare_digest(str(a or ""), str(b or ""))


def get_header(headers: dict, name: str) -> str:
    """Busca um header ignorando diferenças de caixa (Flask normaliza para Title-Case)."""
    alvo = name.lower()
    for k, v in (headers or {}).items():
        if str(k).lower() == alvo:
            return str(v or "")
    return ""


class PaymentProvider(ABC):
    """Contrato mínimo para emissão de boleto/PIX e webhook."""

    codigo: str = ""
    nome: str = ""

    def __init__(self, cfg: dict):
        self.cfg = cfg  # linha de payment_provider_config

    # -- Segurança de webhook ----------------------------------------------

    def webhook_secret(self) -> str:
        """Segredo/token do webhook: config do provedor > env genérica."""
        return (self.cfg.get("webhook_secret") or "").strip() or os.getenv(
            "PAYMENT_WEBHOOK_SECRET", ""
        ).strip()

    def _em_producao(self) -> bool:
        amb = (self.cfg.get("ambiente") or "").lower()
        env = os.getenv("CATALOG_ENV", "development").lower()
        return amb == "producao" or env == "production"

    def validar_assinatura(self, payload: dict, headers: dict, query: dict | None = None) -> None:
        """Valida a autenticidade do webhook.

        Default (Sicoob/mTLS e provedores genéricos): header `X-Webhook-Secret`
        contra o segredo configurado. Provedores com assinatura nativa
        (Mercado Pago, Asaas, EfiPay) sobrescrevem este método.
        Levanta `WebhookNaoAutorizado` se inválido.
        """
        secret = self.webhook_secret()
        if not secret:
            if self._em_producao():
                raise WebhookNaoAutorizado("Webhook sem segredo configurado em produção")
            return  # dev/sandbox sem segredo: aceita
        received = get_header(headers, "X-Webhook-Secret").strip()
        if not const_time_equal(received, secret):
            raise WebhookNaoAutorizado("Webhook não autorizado")

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