"""Provedor Asaas — boleto e PIX (fase 1).

API: https://www.asaas.com/desenvolvedores
Sandbox base: https://sandbox.asaas.com/api/v3
Auth: header `access_token: <api_key>`
Cobrança: POST /payments  (billingType BOLETO|PIX; customer obrigatório)
Boleto no retorno: bankSlipUrl / bankSlip (linhaDigitavel, nossoNumero)
PIX no retorno: pixQrCode / pixQrCodeUrl / invoiceUrl
Webhook: evento PAYMENT_CONFIRMED / PAYMENT_RECEIVED
  header de validação: asaas-access-token (authToken configurado no webhook)
"""
from __future__ import annotations

import requests

from catalog_server.payments.base import PaymentProvider, WebhookNaoAutorizado, const_time_equal, get_header


def _is_pago(status: str) -> bool:
    return status in ("CONFIRMED", "RECEIVED")


class AsaasProvider(PaymentProvider):
    codigo = "asaas"
    nome = "Asaas"

    def __init__(self, cfg: dict):
        super().__init__(cfg)
        base = "https://sandbox.asaas.com/api/v3" if cfg.get("ambiente") != "producao" else "https://www.asaas.com/api/v3"
        self.base = base
        self.api_key = cfg.get("api_key") or cfg.get("access_token") or ""

    def validar_assinatura(self, payload: dict, headers: dict, query: dict | None = None) -> None:
        """Webhook Asaas — header `asaas-access-token` igual ao authToken configurado."""
        secret = self.webhook_secret()
        if not secret:
            if self._em_producao():
                raise WebhookNaoAutorizado("Webhook sem segredo configurado em produção")
            return
        received = get_header(headers, "asaas-access-token").strip()
        if not const_time_equal(received, secret):
            raise WebhookNaoAutorizado("asaas-access-token inválido")

    # -- helpers -----------------------------------------------------------

    def _headers(self) -> dict:
        return {
            "access_token": self.api_key,
            "Content-Type": "application/json",
            "accept": "application/json",
            "User-Agent": "siscom/1.0",
        }

    def _criar_cliente(self, conta: dict) -> str | None:
        """Cria/consulta o cliente no Asaas (CPF/CNPJ como chave). Retorna o id."""
        doc = (conta.get("cliente_doc") or "").replace(".", "").replace("/", "").replace("-", "")
        if not doc:
            return None
        payload = {
            "name": conta.get("cliente") or "Cliente",
            "cpfCnpj": doc,
        }
        # tenta localizar cliente existente por CPF/CNPJ
        r = requests.get(
            f"{self.base}/customers",
            headers=self._headers(),
            params={"cpfCnpj": doc},
            timeout=20,
        )
        if r.ok:
            data = r.json()
            itens = data.get("data") or []
            if itens:
                return itens[0]["id"]
        r = requests.post(f"{self.base}/customers", json=payload, headers=self._headers(), timeout=20)
        if r.ok:
            return r.json().get("id")
        return None

    # -- emissão -----------------------------------------------------------

    def emitir_boleto(self, conta: dict, emitente: dict) -> dict:
        cliente_id = self._criar_cliente(conta)
        body = {
            "customer": cliente_id,
            "billingType": "BOLETO",
            "value": float(conta.get("saldo") or conta.get("valor") or 0),
            "dueDate": conta.get("data_vencimento") or "",
            "description": f"Venda {conta.get('documento') or ''} — {conta.get('descricao') or ''}",
            "externalReference": str(conta.get("documento") or conta.get("id") or ""),
        }
        r = requests.post(f"{self.base}/payments", json=body, headers=self._headers(), timeout=30)
        if not r.ok:
            raise ValueError(f"Asaas: erro ao emitir boleto: {r.status_code} {r.text[:300]}")
        j = r.json()
        bank = j.get("bankSlip") or {}
        return {
            "payment_id": j.get("id"),
            "status_cobranca": "pendente",
            "linha_digitavel": bank.get("line", ""),
            "codigo_barras": bank.get("barcode", ""),
            "nosso_numero": bank.get("identificationField", "") or j.get("nossoNumero", ""),
            "url_boleto": j.get("bankSlipUrl") or "",
        }

    def emitir_pix(self, conta: dict) -> dict:
        cliente_id = self._criar_cliente(conta)
        body = {
            "customer": cliente_id,
            "billingType": "PIX",
            "value": float(conta.get("saldo") or conta.get("valor") or 0),
            "dueDate": conta.get("data_vencimento") or "",
            "description": f"Venda {conta.get('documento') or ''} — {conta.get('descricao') or ''}",
            "externalReference": str(conta.get("documento") or conta.get("id") or ""),
        }
        r = requests.post(f"{self.base}/payments", json=body, headers=self._headers(), timeout=30)
        if not r.ok:
            raise ValueError(f"Asaas: erro ao emitir PIX: {r.status_code} {r.text[:300]}")
        j = r.json()
        return {
            "payment_id": j.get("id"),
            "status_cobranca": "pendente",
            "payload_pix": j.get("pixQrCode") or "",
            "qr_code_base64": j.get("pixQrCodeBase64") or "",
            "txid": j.get("pixTransactionId") or "",
            "url_pix": j.get("invoiceUrl") or "",
        }

    # -- consulta / webhook -------------------------------------------------

    def consultar(self, payment_id: str) -> dict:
        r = requests.get(f"{self.base}/payments/{payment_id}", headers=self._headers(), timeout=20)
        if not r.ok:
            return {"status_cobranca": "erro"}
        j = r.json()
        status = j.get("status") or ""
        return {
            "status_cobranca": "pago" if _is_pago(status) else ("cancelado" if status in ("CANCELLED", "REFUNDED", "DELETED") else "pendente"),
            "status_plataforma": status,
        }

    def webhook(self, payload: dict, headers: dict) -> dict | None:
        """Evento Asaas: {event, payment:{id, status, ...}}."""
        event = payload.get("event")
        if event not in ("PAYMENT_CONFIRMED", "PAYMENT_RECEIVED"):
            return None
        payment = payload.get("payment") or {}
        payment_id = payment.get("id")
        if not payment_id:
            return None
        return {
            "payment_id": str(payment_id),
            "status_cobranca": "pago",
            "webhook_id": f"{event}:{payment_id}",
            "valor": payment.get("value"),
        }