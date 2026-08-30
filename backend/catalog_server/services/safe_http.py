"""Cliente HTTP restrito para URLs fornecidas pelo usuário.

Bloqueia destinos locais/privados, limita redirects e o tamanho baixado para
evitar SSRF e consumo ilimitado de memória/disco.
"""
from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urljoin, urlparse

import requests


class UnsafeUrlError(ValueError):
    pass


def validate_public_url(url: str) -> str:
    parsed = urlparse((url or "").strip())
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise UnsafeUrlError("URL deve usar http:// ou https:// com hostname válido")
    if parsed.username or parsed.password:
        raise UnsafeUrlError("URL com credenciais embutidas não é permitida")

    try:
        addresses = {
            item[4][0]
            for item in socket.getaddrinfo(parsed.hostname, parsed.port or 443, type=socket.SOCK_STREAM)
        }
    except OSError as exc:
        raise UnsafeUrlError("Não foi possível resolver o hostname") from exc

    for address in addresses:
        ip = ipaddress.ip_address(address)
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast or ip.is_unspecified:
            raise UnsafeUrlError("Destino de rede privada ou reservada não é permitido")
    return parsed.geturl()


def get_public(
    url: str,
    *,
    timeout: float = 30,
    headers: dict[str, str] | None = None,
    max_bytes: int = 10 * 1024 * 1024,
    max_redirects: int = 3,
) -> requests.Response:
    current = validate_public_url(url)
    response: requests.Response | None = None
    for _ in range(max_redirects + 1):
        response = requests.get(
            current,
            timeout=timeout,
            headers=headers or {},
            allow_redirects=False,
            stream=True,
        )
        if response.is_redirect or response.status_code in {301, 302, 303, 307, 308}:
            location = response.headers.get("Location")
            response.close()
            if not location:
                raise UnsafeUrlError("Redirect sem destino")
            current = validate_public_url(urljoin(current, location))
            continue

        length = response.headers.get("Content-Length")
        if length and int(length) > max_bytes:
            response.close()
            raise UnsafeUrlError("Resposta excede o limite permitido")
        chunks: list[bytes] = []
        total = 0
        for chunk in response.iter_content(chunk_size=64 * 1024):
            total += len(chunk)
            if total > max_bytes:
                response.close()
                raise UnsafeUrlError("Resposta excede o limite permitido")
            chunks.append(chunk)
        response._content = b"".join(chunks)
        response._content_consumed = True
        return response
    raise UnsafeUrlError("Número máximo de redirects excedido")
