"""Provedor Mercado Pago — boleto e PIX (fase 1).

API: https://www.mercadopago.com.br/developers/pt/docs/sdks-library/overview
Base: https://api.mercadopago.com  (sandbox usa access_token de teste APP_USB/APP_USR)
Auth: header `Authorization: Bearer <access_token>`
PIX: POST /v1/payments  (payment_method_id=pix) -> qr_code, qr_code_base64, ticket_url
Boleto: POST /v1/payments (payment_method_id=bolbradesco) + endereço -> external_resource_url
Webhook: evento `payment` com data.id -> GET /v1/payments/{id} -> status approved
"""
from __future__ import annotations

import requests

from catalog_server.payments.base import PaymentProvider


class MercadoPagoProvider(PaymentProvider):
    codigo = "mercadopago"
    nome = "Mercado Pago"

    def __init__(self, cfg: dict):
        super().__init__(cfg)
        self.base = "https://api.mercadopago.com"
        self.access_token = cfg.get("access_token") or ""

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
            "X-Idempotency-Key": self.cfg.get("payment_id") or "siscom",
        }

    def _body(self, conta: dict, metodo: str, emitente: dict | None = None) -> dict:
        doc = (conta.get("cliente_doc") or "").replace(".", "").replace("/", "").replace("-", "")
        tipo_doc = "CNPJ" if len(doc) == 14 else "CPF" if len(doc) == 11 else "CPF"
        body: dict = {
            "transaction_amount": float(conta.get("saldo") or conta.get("valor") or 0),
            "description": f"Venda {conta.get('documento') or ''}",
            "payment_method_id": metodo,
            "payer": {
                "email": (conta.get("cliente_email") or "cliente@exemplo.com"),
                "identification": {"type": tipo_doc, "number": doc or "0"},
                "first_name": (conta.get("cliente") or "Cliente"),
            },
            "external_reference": str(conta.get("documento") or conta.get("id") or ""),
            "notification_url": self.cfg.get("webhook_url") or "",
        }
        if metodo == "bolbradesco" and emitente:
            body["payer"]["address"] = {
                "zip_code": emitente.get("cep") or "",
                "street_name": emitente.get("logradouro") or "",
                "street_number": emitente.get("numero") or "S/N",
                "neighborhood": emitente.get("bairro") or "",
                "city": emitente.get("municipio") or "",
                "federal_unit": emitente.get("uf") or "",
            }
        return body

    # -- emissão -----------------------------------------------------------

    def emitir_boleto(self, conta: dict, emitente: dict) -> dict:
        body = self._body(conta, "bolbradesco", emitente)
        r = requests.post(f"{self.base}/v1/payments", json=body, headers=self._headers(), timeout=30)
        if not r.ok:
            raise ValueError(f"Mercado Pago: erro ao emitir boleto: {r.status_code} {r.text[:300]}")
        j = r.json()
        return {
            "payment_id": str(j.get("id")),
            "status_cobranca": "pendente" if j.get("status") != "approved" else "pago",
            "linha_digitavel": "",
            "codigo_barras": "",
            "nosso_numero": "",
            "url_boleto": j.get("external_resource_url") or "",
        }

    def emitir_pix(self, conta: dict) -> dict:
        body = self._body(conta, "pix")
        r = requests.post(f"{self.base}/v1/payments", json=body, headers=self._headers(), timeout=30)
        if not r.ok:
            raise ValueError(f"Mercado Pago: erro ao emitir PIX: {r.status_code} {r.text[:300]}")
        j = r.json()
        return {
            "payment_id": str(j.get("id")),
            "status_cobranca": "pendente" if j.get("status") != "approved" else "pago",
            "payload_pix": (j.get("point_of_interaction") or {}).get("transaction_data", {}).get("qr_code") or "",
            "qr_code_base64": (j.get("point_of_interaction") or {}).get("transaction_data", {}).get("qr_code_base64") or "",
            "txid": (j.get("point_of_interaction") or {}).get("transaction_data", {}).get("qr_code") or "",
            "url_pix": (j.get("point_of_interaction") or {}).get("transaction_data", {}).get("ticket_url") or "",
        }

    # -- consulta / webhook -------------------------------------------------

    def consultar(self, payment_id: str) -> dict:
        r = requests.get(f"{self.base}/v1/payments/{payment_id}", headers=self._headers(), timeout=20)
        if not r.ok:
            return {"status_cobranca": "erro"}
        j = r.json()
        status = j.get("status") or ""
        return {
            "status_cobranca": "pago" if status == "approved" else ("cancelado" if status in ("cancelled", "refunded") else "pendente"),
            "status_plataforma": status,
        }

    def webhook(self, payload: dict, headers: dict) -> dict | None:
        """Evento Mercado Pago: {type:'payment', data:{id}}."""
        if payload.get("type") != "payment":
            return None
        data = payload.get("data") or {}
        payment_id = data.get("id")
        if not payment_id:
            return None
        # consulta o status para confirmar pagamento
        st = self.consultar(str(payment_id))
        if st["status_cobranca"] != "pago":
            return None
        return {
            "payment_id": str(payment_id),
            "status_cobranca": "pago",
            "webhook_id": f"payment:{payment_id}",
        }