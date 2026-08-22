"""Cliente HTTP para o microserviço "Cotações IA Importer".

Usa apenas a stdlib (urllib) para não adicionar dependências ao monólito.
Extrai/procura no Qdrant via endpoints do microserviço.
"""

from __future__ import annotations

import json
import mimetypes
import urllib.error
import urllib.request
import uuid

from catalog_server.config import IA_TIMEOUT, IA_URL

API = IA_URL


class ImporterError(Exception):
    pass


def _post_json(path: str, payload: dict) -> dict:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        f"{API}{path}",
        data=body,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        method="POST",
    )
    return _parsed(req)


def health() -> bool:
    """Checa só a conectividade com o microserviço (sem acionar o LLM)."""
    try:
        req = urllib.request.Request(f"{API}/health", method="GET")
        with urllib.request.urlopen(req, timeout=IA_TIMEOUT) as resp:
            return resp.status == 200
    except (urllib.error.URLError, urllib.error.HTTPError):
        return False


def _parsed(req: urllib.request.Request) -> dict:
    try:
        with urllib.request.urlopen(req, timeout=IA_TIMEOUT) as resp:
            data = resp.read()
            if not data:
                return {}
            return json.loads(data.decode("utf-8"))
    except urllib.error.HTTPError as exc:
        try:
            detail = json.loads(exc.read().decode("utf-8")).get("detail", "")
        except Exception:
            detail = ""
        raise ImporterError(
            f"Microserviço IA falhou (HTTP {exc.code}){(' — ' + str(detail)) if detail else ''}"
        ) from exc
    except urllib.error.URLError as exc:
        raise ImporterError(
            f"Não foi possível acessar o microserviço IA em {API}: {exc.reason}"
        ) from exc


def extract(texto: str) -> dict:
    return _post_json("/api/extract", {"text": texto})


def extract_pdf(data: bytes, filename: str = "arquivo.pdf") -> dict:
    boundary = "----ia" + uuid.uuid4().hex
    pre = (
        f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; "
        f'filename="{filename}"\r\nContent-Type: {mimetypes.guess_type(filename)[0] or "application/pdf"}\r\n\r\n'
    ).encode("utf-8")
    body = pre + data + f"\r\n--{boundary}--\r\n".encode("utf-8")
    req = urllib.request.Request(
        f"{API}/api/extract/file",
        data=body,
        headers={
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "Accept": "application/json",
        },
        method="POST",
    )
    return _parsed(req)


def match(items: list[dict], limite: int = 5) -> dict:
    return _post_json("/api/match", {"items": items, "top_k": limite})


def seed(produtos: list[dict], reset: bool = False) -> dict:
    return _post_json(
        "/api/catalog/seed", {"produtos": produtos, "reset": bool(reset)}
    )