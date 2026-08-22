"""Cliente SEFAZ via API Focus NFe (FASE 9).

A integração de emissão usa a API REST da Focus NFe (o emitente já tem
`token_focus` e `ambiente_focus`). Este módulo envia o XML gerado e interpreta a
resposta (autorizada/rejeitada).

Sem `token_focus` configurado, a emissão fica apenas como `digitada` (armazenada)
— a comunicação real exige credencial de homologação/produção.
"""
from __future__ import annotations

import json
import urllib.request

BASE = "https://api.focusnfe.com.br"


def enviar(nfe: dict, token: str | None = None, ambiente: str = "homologacao") -> dict:
    if not token:
        return {"enviado": False, "motivo": "token_focus não configurado — nota armazenada como 'digitada'"}
    url = f"{BASE}/v2/nfe?ref={nfe.get('chave', '')}"
    payload = json.dumps({"nota_fiscal": json.loads(nfe.get("xml", "{}"))}, ensure_ascii=False) if nfe.get("xml", "").lstrip().startswith("{") else nfe["xml"]
    req = urllib.request.Request(
        url,
        data=payload.encode("utf-8"),
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = resp.read().decode("utf-8")
            return {"enviado": True, "status_http": resp.status, "resposta": body[:2000]}
    except urllib.error.HTTPError as e:
        return {"enviado": False, "status_http": e.code, "resposta": e.read().decode("utf-8", "replace")[:2000]}
    except Exception as e:  # noqa: BLE001
        return {"enviado": False, "motivo": str(e)}
