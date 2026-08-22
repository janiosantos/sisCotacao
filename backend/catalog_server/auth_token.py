"""Emissão e validação de token de API (HMAC, stateless, sem dependências).

O token é `base64url(payload).hmac(secret)`. O `payload` traz `sub` (id do
usuário), `login`, `perfil` e `exp` (expiração). A validação confere a
assinatura e a expiração; falhas retornam `None`.

A chave é `config.SECRET_KEY` (env `CATALOG_SECRET`).
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time

from catalog_server import config

TTL_SECONDS = 60 * 60 * 24 * 7  # 7 dias


def _sign(data_b64: str) -> str:
    return hmac.new(
        config.SECRET_KEY.encode(), data_b64.encode(), hashlib.sha256
    ).hexdigest()


def criar_token(usuario: dict, ttl: int = TTL_SECONDS) -> str:
    payload = {
        "sub": usuario.get("id"),
        "login": usuario.get("login"),
        "perfil": usuario.get("perfil"),
        "exp": int(time.time()) + ttl,
    }
    data = (
        base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip("=")
    )
    return f"{data}.{_sign(data)}"


def validar_token(token: str | None) -> dict | None:
    if not token or "." not in token:
        return None
    data, sig = token.rsplit(".", 1)
    if not hmac.compare_digest(_sign(data), sig):
        return None
    try:
        pad = "=" * (-len(data) % 4)
        payload = json.loads(base64.urlsafe_b64decode(data + pad))
    except Exception:
        return None
    if payload.get("exp", 0) < int(time.time()):
        return None
    return payload
