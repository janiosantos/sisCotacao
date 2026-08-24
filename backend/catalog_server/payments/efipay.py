"""Provedor EfiPay — boleto e PIX (FASE 2).

API: https://dev.efipay.com.br/docs/api-pix/credenciais/
Autenticação: OAuth2 client credentials (HTTP Basic com client_id:client_secret)
  + certificado P12/PEM obrigatório (mTLS) para a API Pix.
- PIX (sandbox base https://pix-h.api.efipay.com.br): POST /v2/cob
- Boleto (cobranças, sandbox base https://cobrancas-h.api.efipay.com.br):
  POST /v1/charges com payment.banking_billet
"""
from __future__ import annotations

import requests

from catalog_server.payments.base import PaymentProvider


class EfiPayProvider(PaymentProvider):
    codigo = "efipay"
    nome = "EfiPay"

    def __init__(self, cfg: dict):
        super().__init__(cfg)
        sandbox = cfg.get("ambiente") != "producao"
        self.client_id = cfg.get("client_id") or ""
        self.client_secret = cfg.get("client_secret") or ""
        self.cert = cfg.get("certificado") or ""
        self.chave_pix = cfg.get("chave_pix") or ""
        if sandbox:
            self.base_pix = "https://pix-h.api.efipay.com.br"
            self.base_cob = "https://cobrancas-h.api.efipay.com.br"
        else:
            self.base_pix = "https://pix.api.efipay.com.br"
            self.base_cob = "https://cobrancas.api.efipay.com.br"

    # -- helpers -----------------------------------------------------------

    def _auth(self, base: str, scope: str) -> str:
        if not self.client_id or not self.client_secret:
            raise ValueError("EfiPay: informe client_id e client_secret")
        if not self.cert:
            raise ValueError("EfiPay: informe o certificado (P12/PEM) para autenticar")
        url = f"{base}/oauth/token"
        r = requests.post(
            url,
            data={"grant_type": "client_credentials"},
            auth=(self.client_id, self.client_secret),
            cert=self.cert,
            timeout=20,
        )
        if not r.ok:
            raise ValueError(f"EfiPay: falha na autenticação: {r.status_code} {r.text[:300]}")
        return r.json().get("access_token") or ""

    def _headers(self, token: str) -> dict:
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "accept": "application/json",
        }

    def _devedor(self, conta: dict) -> dict:
        doc = (conta.get("cliente_doc") or "").replace(".", "").replace("/", "").replace("-", "")
        campo = "cnpj" if len(doc) == 14 else "cpf"
        return {
            "nome": (conta.get("cliente") or "Cliente")[:140],
            campo: doc or "00000000000",
        }

    # -- emissão -----------------------------------------------------------

    def emitir_boleto(self, conta: dict, emitente: dict) -> dict:
        token = self._auth(self.base_cob, "cobranca")
        body = {
            "customer": {
                "name": (conta.get("cliente") or "Cliente")[:140],
                "cpfCnpj": (conta.get("cliente_doc") or "").replace(".", "").replace("/", "").replace("-", ""),
            },
            "billingInstructions": "Pagamento referente à venda " + str(conta.get("documento") or ""),
            "items": [{"name": conta.get("descricao") or "Conta a receber", "value": int(round(float(conta.get("saldo") or 0) * 100)), "amount": 1}],
            "payment": {
                "banking_billet": {
                    "expire_at": conta.get("data_vencimento") or "",
                    "customer": self._devedor(conta),
                    "instructions": "Recebimento de venda a prazo",
                }
            },
        }
        r = requests.post(f"{self.base_cob}/v1/charges", json=body, headers=self._headers(token), cert=self.cert, timeout=30)
        if not r.ok:
            raise ValueError(f"EfiPay: erro ao emitir boleto: {r.status_code} {r.text[:300]}")
        j = r.json()
        bil = ((j.get("payment") or {}).get("banking_billet")) or {}
        return {
            "payment_id": str(j.get("id")),
            "status_cobranca": "pendente",
            "linha_digitavel": bil.get("linha_digitavel") or "",
            "codigo_barras": bil.get("barcode") or "",
            "nosso_numero": bil.get("nosso_numero") or "",
            "url_boleto": bil.get("link") or "",
        }

    def emitir_pix(self, conta: dict) -> dict:
        if not self.chave_pix:
            raise ValueError("EfiPay: informe a chave PIX na configuração")
        token = self._auth(self.base_pix, "cob")
        valor = f"{float(conta.get('saldo') or conta.get('valor') or 0):.2f}"
        body = {
            "calendario": {"expiracao": 3600},
            "devedor": self._devedor(conta),
            "valor": {"original": valor},
            "chave": self.chave_pix,
            "solicitacaoPagador": "Recebimento de venda a prazo",
        }
        r = requests.post(f"{self.base_pix}/v2/cob", json=body, headers=self._headers(token), cert=self.cert, timeout=30)
        if not r.ok:
            raise ValueError(f"EfiPay: erro ao emitir PIX: {r.status_code} {r.text[:300]}")
        j = r.json()
        loc = j.get("loc") or {}
        return {
            "payment_id": str(j.get("txid") or j.get("id") or ""),
            "status_cobranca": "pendente",
            "payload_pix": j.get("pixCopiaECola") or "",
            "qr_code_base64": "",
            "txid": j.get("txid") or "",
            "url_pix": loc.get("location") or "",
        }

    # -- consulta / webhook -------------------------------------------------

    def consultar(self, payment_id: str) -> dict:
        if not payment_id:
            return {"status_cobranca": "erro"}
        token = self._auth(self.base_pix, "cob.read")
        r = requests.get(f"{self.base_pix}/v2/cob/{payment_id}", headers=self._headers(token), cert=self.cert, timeout=20)
        if not r.ok:
            return {"status_cobranca": "erro"}
        j = r.json()
        status = j.get("status") or ""
        return {
            "status_cobranca": "pago" if status == "CONCLUIDA" else ("cancelado" if status == "REMOVIDA_PELO_USUARIO_RECEBEDOR" else "pendente"),
            "status_plataforma": status,
        }

    def webhook(self, payload: dict, headers: dict) -> dict | None:
        """Webhook EfiPay: {type:'pix.received'|'charge', pix:{txid,...}, charge:{id,status}}."""
        tipo = payload.get("type") or ""
        if "pix" in tipo or payload.get("pix"):
            pix = payload.get("pix") or {}
            if pix.get("status") == "PAGO" or tipo == "pix.received":
                txid = pix.get("txid") or ""
                if txid:
                    return {"payment_id": str(txid), "status_cobranca": "pago",
                            "webhook_id": f"pix:{txid}", "valor": pix.get("valor")}
        charge = payload.get("charge") or {}
        if charge.get("status") == "paid":
            cid = charge.get("id") or ""
            if cid:
                return {"payment_id": str(cid), "status_cobranca": "pago",
                        "webhook_id": f"charge:{cid}"}
        return None