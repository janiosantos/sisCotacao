"""Provedor Mercado Pago — boleto e PIX (fase 1).

API: https://www.mercadopago.com.br/developers/pt/docs/sdks-library/overview
Base: https://api.mercadopago.com  (sandbox usa access_token de teste APP_USB/APP_USR)
Auth: header `Authorization: Bearer <access_token>`
PIX: POST /v1/payments  (payment_method_id=pix) -> qr_code, qr_code_base64, ticket_url
Boleto: POST /v1/payments (payment_method_id=bolbradesco) + endereço -> external_resource_url
Webhook: evento `payment` com data.id -> GET /v1/payments/{id} -> status approved
"""
from __future__ import annotations

import hashlib
import hmac
import os
import time

import requests

from catalog_server.payments.base import PaymentProvider, WebhookNaoAutorizado, const_time_equal, get_header


class MercadoPagoProvider(PaymentProvider):
    codigo = "mercadopago"
    nome = "Mercado Pago"

    def __init__(self, cfg: dict):
        super().__init__(cfg)
        self.base = "https://api.mercadopago.com"
        self.access_token = cfg.get("access_token") or ""

    def validar_assinatura(self, payload: dict, headers: dict, query: dict | None = None) -> None:
        """Webhook Mercado Pago — `x-signature: ts=<ms>,v1=<hmac-sha256 hex>`.

        Manifest: `id:<data.id>;request-id:<x-request-id>;ts:<ts>;` (pares ausentes
        omitidos; data.id em minúsculas). HMAC-SHA256 com o segredo configurado.
        Anti-replay: `ts` dentro da janela `WEBHOOK_TS_WINDOW_MS` (default 5 min).
        """
        secret = self.webhook_secret()
        if not secret:
            if self._em_producao():
                raise WebhookNaoAutorizado("Webhook sem segredo configurado em produção")
            return  # sandbox sem segredo: aceita
        x_sig = get_header(headers, "x-signature").strip()
        if not x_sig:
            raise WebhookNaoAutorizado("Header x-signature ausente")
        partes: dict[str, str] = {}
        for peca in x_sig.split(","):
            if "=" in peca:
                k, v = peca.split("=", 1)
                partes[k.strip()] = v.strip()
        ts = partes.get("ts")
        v1 = partes.get("v1")
        if not ts or not v1:
            raise WebhookNaoAutorizado("x-signature sem ts/v1")

        # anti-replay: janela de tolerância
        try:
            ts_ms = int(ts)
        except ValueError:
            raise WebhookNaoAutorizado("ts inválido em x-signature")
        janela = int(os.getenv("WEBHOOK_TS_WINDOW_MS", str(5 * 60 * 1000)))
        if abs(int(time.time() * 1000) - ts_ms) > janela:
            raise WebhookNaoAutorizado("Webhook expirado (ts fora da janela)")

        # manifest oficial do Mercado Pago
        data_id = str((query or {}).get("data.id") or ((payload.get("data") or {}).get("id") or "")).lower()
        x_req = get_header(headers, "x-request-id").strip()
        manifest_parts: list[str] = []
        if data_id:
            manifest_parts.append(f"id:{data_id}")
        if x_req:
            manifest_parts.append(f"request-id:{x_req}")
        manifest_parts.append(f"ts:{ts}")
        manifest = ";".join(manifest_parts) + ";"

        calc = hmac.new(secret.encode(), manifest.encode(), hashlib.sha256).hexdigest()
        if not const_time_equal(calc, v1.lower()):
            raise WebhookNaoAutorizado("Assinatura inválida (x-signature)")

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