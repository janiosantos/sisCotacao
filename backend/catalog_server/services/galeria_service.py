"""Contrato seguro entre o ERP e a galeria standalone de produtos."""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import time
from urllib.parse import urlencode

import requests

from catalog_server import config
from catalog_server.services import imagens_service


MAX_SELECTION = 12
MAX_IMAGE_BYTES = 15 * 1024 * 1024
_EXTENSION_BY_TYPE = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/gif": ".gif",
    "image/webp": ".webp",
    "image/bmp": ".bmp",
    "image/avif": ".avif",
}


class GalleryUnavailable(RuntimeError):
    pass


class GalleryImageNotFound(ValueError):
    pass


def _encoded(payload: dict) -> str:
    raw = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode()
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def _session_token(usuario_id: int) -> str:
    encoded = _encoded(
        {
            "uid": int(usuario_id),
            "exp": int(time.time()) + 5 * 60,
            "nonce": secrets.token_urlsafe(12),
        }
    )
    signature = hmac.new(
        config.GALLERY_SESSION_SECRET.encode(), encoded.encode(), hashlib.sha256
    ).hexdigest()
    return f"{encoded}.{signature}"


def _service_token() -> str:
    return hmac.new(
        config.GALLERY_SESSION_SECRET.encode(),
        b"siscom-gallery-service",
        hashlib.sha256,
    ).hexdigest()


def _valid_image_content(content_type: str, content: bytes) -> bool:
    if content_type in {"image/jpeg", "image/png", "image/gif", "image/webp"}:
        return imagens_service._image_size(content) is not None
    if content_type == "image/bmp":
        return len(content) >= 14 and content[:2] == b"BM"
    if content_type == "image/avif":
        return len(content) >= 16 and content[4:8] == b"ftyp" and b"avif" in content[8:32]
    return False


def status(usuario_id: int) -> dict:
    available = False
    try:
        with requests.get(f"{config.GALLERY_INTERNAL_URL}/health", timeout=2) as response:
            available = response.ok and bool(response.json().get("ok"))
    except (requests.RequestException, ValueError):
        available = False
    query = urlencode(
        {
            "session": _session_token(usuario_id),
            "select": "1",
            "max_selection": MAX_SELECTION,
        }
    )
    separator = "&" if "?" in config.GALLERY_PUBLIC_URL else "?"
    return {
        "available": available,
        "url": f"{config.GALLERY_PUBLIC_URL}{separator}{query}",
        "max_selection": MAX_SELECTION,
    }


def _download(image_id: int) -> tuple[bytes, str, str]:
    try:
        response = requests.get(
            f"{config.GALLERY_INTERNAL_URL}/api/images/{image_id}/download",
            headers={"Authorization": f"Bearer {_service_token()}"},
            timeout=(3, 30),
            stream=True,
        )
        with response:
            if response.status_code == 404:
                raise GalleryImageNotFound(f"Imagem {image_id} nao encontrada na galeria")
            if not response.ok:
                raise GalleryUnavailable(f"Galeria respondeu HTTP {response.status_code}")
            content_type = response.headers.get("Content-Type", "").split(";", 1)[0].lower()
            extension = _EXTENSION_BY_TYPE.get(content_type)
            if not extension:
                raise ValueError(f"Imagem {image_id} possui formato nao permitido")
            declared = response.headers.get("Content-Length")
            if declared:
                try:
                    declared_bytes = int(declared)
                except ValueError as exc:
                    raise ValueError(f"Tamanho declarado da imagem {image_id} e invalido") from exc
                if declared_bytes > MAX_IMAGE_BYTES:
                    raise ValueError(f"Imagem {image_id} excede 15 MB")
            chunks: list[bytes] = []
            total = 0
            for chunk in response.iter_content(1024 * 1024):
                total += len(chunk)
                if total > MAX_IMAGE_BYTES:
                    raise ValueError(f"Imagem {image_id} excede 15 MB")
                chunks.append(chunk)
            content = b"".join(chunks)
            if not content:
                raise ValueError(f"Imagem {image_id} esta vazia")
            if not _valid_image_content(content_type, content):
                raise ValueError(f"Conteudo da imagem {image_id} e invalido")
            expected_hash = response.headers.get("X-Image-SHA256", "")
            actual_hash = hashlib.sha256(content).hexdigest()
            if not expected_hash or not hmac.compare_digest(expected_hash, actual_hash):
                raise ValueError(f"Checksum da imagem {image_id} diverge do manifesto")
            return content, extension, actual_hash
    except requests.RequestException as exc:
        raise GalleryUnavailable(f"Galeria indisponivel: {exc}") from exc


def importar(produto_id: int, image_ids: list[int], repo) -> dict:
    unique_ids = list(dict.fromkeys(int(value) for value in image_ids))
    if not unique_ids:
        raise ValueError("Selecione ao menos uma imagem")
    if len(unique_ids) > MAX_SELECTION:
        raise ValueError(f"Selecione no maximo {MAX_SELECTION} imagens por vez")

    saved: list[str] = []
    deduplicated = 0
    try:
        for image_id in unique_ids:
            content, extension, digest = _download(image_id)
            relative = imagens_service.salvar_conteudo_galeria(
                produto_id,
                content,
                extension,
                digest,
                image_id,
            )
            if relative:
                saved.append(relative)
            else:
                deduplicated += 1
        repo.add_imagens(produto_id, saved)
    except Exception:
        for relative in saved:
            imagens_service.remover_arquivo(relative)
        raise
    return {"saved": saved, "deduplicated": deduplicated}
