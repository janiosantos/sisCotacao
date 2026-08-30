"""SEFAZAdapter via Focus NFe — NF-e (55) e NFC-e (65).

Doc oficial: https://doc.focusnfe.com.br/reference/introducao
Autenticação: HTTP Basic com o token da conta (login=token, senha=vazio).
Endpoints usados (v2): criação/consulta/cancelamento de NFe e NFCe.

Configuração vem de `tecnospeed_config_repo` (campos ambiente/token são
compartilhados como ponto único de segredo até migração dedicada).
"""
from __future__ import annotations

import requests

_BASE = "https://api.focusnfe.com.br/v2"
_TIMEOUT = 40


class FocusError(Exception):
    pass


def _auth(token: str) -> tuple[str, str]:
    return (token, "")


def _url(ambiente: str, recurso: str, acao: str = "") -> str:
    ref = "nfe" if recurso == "55" else "nfce"
    sufixo = {"": "", "cancel": "/cancel"}.get(acao, f"/{acao}" if acao else "")
    prefixo = "homologacao_" if ambiente == "homologacao" else ""
    return f"{_BASE}/{prefixo}{ref}{sufixo}.json"


def emitir(
    *,
    ambiente: str,
    token: str,
    modelo: str,
    payload: dict,
    referencia_externa: str,
) -> dict:
    """Cria NF-e/NFC-e (modelo 55/65). `payload` segue o layout Focus."""
    try:
        r = requests.post(
            _url(ambiente, modelo),
            auth=_auth(token),
            json=payload,
            timeout=_TIMEOUT,
        )
        r.raise_for_status()
        return r.json()
    except requests.RequestException as e:
        raise FocusError(f"Focus emissão falhou: {e}") from e


def consultar(*, ambiente: str, token: str, modelo: str, referencia_externa: str) -> dict:
    try:
        r = requests.get(
            _url(ambiente, modelo),
            auth=_auth(token),
            params={"ref": referencia_externa},
            timeout=_TIMEOUT,
        )
        r.raise_for_status()
        return r.json()
    except requests.RequestException as e:
        raise FocusError(f"Focus consulta falhou: {e}") from e


def cancelar(
    *, ambiente: str, token: str, modelo: str,
    referencia_externa: str, justificativa: str,
) -> dict:
    body = {"justificativa": justificativa[:255]}
    try:
        r = requests.post(
            _url(ambiente, modelo, "cancel"),
            auth=_auth(token),
            data={**body, "ref": referencia_externa},
            timeout=_TIMEOUT,
        )
        r.raise_for_status()
        return r.json()
    except requests.RequestException as e:
        raise FocusError(f"Focus cancelamento falhou: {e}") from e
