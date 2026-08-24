"""Provedor Sicoob — boleto e PIX (FASE 2).

API: https://developers.sicoob.com.br/portal/documentacao
- Sandbox: token Bearer de teste direto (config access_token) + header client_id.
- Produção: OAuth2 client credentials com certificado ICP-Brasil (PFX) + client_id.
Boleto (Cobrança V3): sandbox base .../cobranca-bancaria/v3
PIX: sandbox base .../pix/api/v2
"""
from __future__ import annotations

import requests

from catalog_server.payments.base import PaymentProvider


class SicoobProvider(PaymentProvider):
    codigo = "sicoob"
    nome = "Sicoob"

    def __init__(self, cfg: dict):
        super().__init__(cfg)
        self.client_id = cfg.get("client_id") or ""
        self.client_secret = cfg.get("client_secret") or ""
        self.access_token = cfg.get("access_token") or ""
        self.cert = cfg.get("certificado") or ""
        self.numero_contrato = cfg.get("conta") or ""
        self.ambiente = cfg.get("ambiente") or "sandbox"
        if self.ambiente == "producao":
            self.base = "https://apis.sisbr.com.br/cooperado"
        else:
            self.base = "https://sandbox.sicoob.com.br/sicoob/sandbox"

    # -- helpers -----------------------------------------------------------

    def _token(self) -> str:
        if self.ambiente != "producao":
            if not self.access_token:
                raise ValueError("Sicoob sandbox: informe o access_token de teste")
            return self.access_token
        # produção: OAuth2 client credentials + certificado
        if not self.client_id or not self.cert:
            raise ValueError("Sicoob: informe client_id e certificado (PFX) para produção")
        r = requests.post(
            "https://auth.sicoob.com.br/auth/realms/cooperado/protocol/openid-connect/token",
            data={
                "grant_type": "client_credentials",
                "client_id": self.client_id,
                "client_secret": self.client_secret or "",
                "scope": "cobranca-bancaria-boleto-escritural-read cobranca-bancaria-boleto-escritural-write pix.write pix.read",
            },
            cert=self.cert,
            timeout=20,
        )
        if not r.ok:
            raise ValueError(f"Sicoob: falha na autenticação: {r.status_code} {r.text[:300]}")
        return r.json().get("access_token") or ""

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self._token()}",
            "client_id": self.client_id,
            "Content-Type": "application/json",
            "accept": "application/json",
        }

    def _pagador(self, conta: dict) -> dict:
        doc = (conta.get("cliente_doc") or "").replace(".", "").replace("/", "").replace("-", "")
        return {
            "tipoPessoa": "JURIDICA" if len(doc) == 14 else "FISICA",
            "documento": doc or "00000000000",
            "nome": (conta.get("cliente") or "Cliente"),
        }

    # -- emissão -----------------------------------------------------------

    def emitir_boleto(self, conta: dict, emitente: dict) -> dict:
        if not self.numero_contrato:
            raise ValueError("Sicoob: informe o número do contrato (campo 'Conta') para boleto")
        body = {
            "numeroContrato": self.numero_contrato,
            "modalidade": 1,
            "dataVencimento": conta.get("data_vencimento") or "",
            "valorOriginal": float(conta.get("saldo") or conta.get("valor") or 0),
            "pagador": self._pagador(conta),
            "beneficiarioFinal": {"documento": (emitente or {}).get("cnpj") or "", "nome": (emitente or {}).get("razao_social") or ""},
            "seuNumero": str(conta.get("documento") or conta.get("id") or ""),
            "indicadorAceite": "N",
            "instrucao1": "Recebimento de venda a prazo",
        }
        r = requests.post(f"{self.base}/cobranca-bancaria/v3/boletos", json=body, headers=self._headers(), timeout=30)
        if not r.ok:
            raise ValueError(f"Sicoob: erro ao emitir boleto: {r.status_code} {r.text[:300]}")
        j = r.json()
        return {
            "payment_id": str(j.get("id") or j.get("nossoNumero") or ""),
            "status_cobranca": "pendente",
            "linha_digitavel": j.get("linhaDigitavel") or "",
            "codigo_barras": j.get("codigoBarras") or "",
            "nosso_numero": str(j.get("nossoNumero") or ""),
            "url_boleto": "",
        }

    def emitir_pix(self, conta: dict) -> dict:
        if not self.cfg.get("chave_pix"):
            raise ValueError("Sicoob: informe a chave PIX na configuração")
        body = {
            "calendario": {"expiracao": 3600},
            "devedor": self._pagador(conta),
            "valor": {"original": f"{float(conta.get('saldo') or conta.get('valor') or 0):.2f}"},
            "chave": self.cfg.get("chave_pix") or "",
        }
        r = requests.post(f"{self.base}/pix/api/v2/cob", json=body, headers=self._headers(), timeout=30)
        if not r.ok:
            raise ValueError(f"Sicoob: erro ao emitir PIX: {r.status_code} {r.text[:300]}")
        j = r.json()
        loc = j.get("loc") or {}
        return {
            "payment_id": str(j.get("txid") or ""),
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
        r = requests.get(f"{self.base}/pix/api/v2/cob/{payment_id}", headers=self._headers(), timeout=20)
        if not r.ok:
            return {"status_cobranca": "erro"}
        j = r.json()
        status = j.get("status") or ""
        return {
            "status_cobranca": "pago" if status == "CONCLUIDA" else ("cancelado" if status in ("REMOVIDA_PELO_USUARIO_RECEBEDOR", "CANCELADA") else "pendente"),
            "status_plataforma": status,
        }

    def webhook(self, payload: dict, headers: dict) -> dict | None:
        """Webhook Sicoob PIX: {pix:[{txid, valor, ...}]}."""
        pix_list = payload.get("pix") or []
        for pix in pix_list:
            txid = pix.get("txid") or ""
            if txid:
                return {
                    "payment_id": str(txid),
                    "status_cobranca": "pago",
                    "webhook_id": f"pix:{txid}",
                    "valor": pix.get("valor"),
                }
        return None