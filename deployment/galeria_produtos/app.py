"""Galeria standalone das imagens legadas de produtos.

O processo e os dados desta aplicacao ficam fora do SISCOM. O ERP somente
emite uma sessao curta para o navegador e importa imagens por um endpoint
autenticado entre servicos.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import mimetypes
import os
import re
import sqlite3
import time
from contextlib import closing
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, quote, unquote, urlparse


HOST = os.getenv("GALLERY_HOST", "0.0.0.0")
PORT = int(os.getenv("GALLERY_PORT", "8091"))
BASE_PATH = "/" + os.getenv("GALLERY_BASE_PATH", "/galeria").strip("/")
DATA_DIR = Path(os.getenv("GALLERY_DATA_DIR", "/data")).resolve()
DB_PATH = DATA_DIR / "gallery.sqlite3"
MEDIA_DIR = (DATA_DIR / "media").resolve()
SESSION_SECRET = os.getenv("GALLERY_SESSION_SECRET", "")
MAX_PAGE_SIZE = 100


def _b64decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def _service_token() -> str:
    return hmac.new(SESSION_SECRET.encode(), b"siscom-gallery-service", hashlib.sha256).hexdigest()


def _valid_session(token: str) -> bool:
    try:
        encoded, signature = token.split(".", 1)
        expected = hmac.new(SESSION_SECRET.encode(), encoded.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(signature, expected):
            return False
        payload = json.loads(_b64decode(encoded))
        return int(payload.get("exp", 0)) >= int(time.time()) and bool(payload.get("uid"))
    except (ValueError, TypeError, json.JSONDecodeError):
        return False


def _valid_bearer(header: str | None) -> bool:
    if not SESSION_SECRET or not header or not header.startswith("Bearer "):
        return False
    token = header[7:].strip()
    return hmac.compare_digest(token, _service_token()) or _valid_session(token)


def _signed_media_url(relative_path: str) -> str:
    expires = int(time.time()) + 900
    payload = f"{relative_path}\n{expires}"
    signature = hmac.new(SESSION_SECRET.encode(), payload.encode(), hashlib.sha256).hexdigest()
    return f"{BASE_PATH}/media/{quote(relative_path)}?exp={expires}&sig={signature}"


def _valid_media_signature(relative_path: str, params: dict[str, list[str]]) -> bool:
    try:
        expires = int((params.get("exp") or ["0"])[0])
    except ValueError:
        return False
    if expires < int(time.time()):
        return False
    signature = (params.get("sig") or [""])[0]
    payload = f"{relative_path}\n{expires}"
    expected = hmac.new(SESSION_SECRET.encode(), payload.encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(signature, expected)


def _safe_media_path(relative_path: str) -> Path | None:
    try:
        path = (MEDIA_DIR / unquote(relative_path)).resolve()
        path.relative_to(MEDIA_DIR)
    except (ValueError, OSError):
        return None
    return path if path.is_file() else None


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(f"file:{DB_PATH.as_posix()}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def _fts_query(term: str) -> str:
    words = re.findall(r"[\w-]+", term, flags=re.UNICODE)
    return " AND ".join(f'"{word.replace(chr(34), "")}"*' for word in words[:8])


class GalleryHandler(BaseHTTPRequestHandler):
    server_version = "SiscomGallery/1.0"

    def log_message(self, fmt: str, *args) -> None:
        if self.path.endswith("/health"):
            return
        super().log_message(fmt, *args)

    def _headers(self, status: int, content_type: str, length: int | None = None) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "same-origin")
        self.send_header("Cache-Control", "no-store" if "json" in content_type else "private, max-age=900")
        self.send_header(
            "Content-Security-Policy",
            "default-src 'self'; img-src 'self' data:; style-src 'self'; script-src 'self'; frame-ancestors 'self'",
        )
        if length is not None:
            self.send_header("Content-Length", str(length))
        self.end_headers()

    def _json(self, payload: object, status: int = HTTPStatus.OK) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode()
        self._headers(status, "application/json; charset=utf-8", len(body))
        self.wfile.write(body)

    def _unauthorized(self) -> None:
        self._json({"error": "Sessao da galeria invalida ou expirada"}, HTTPStatus.UNAUTHORIZED)

    def _serve_static(self, filename: str, content_type: str) -> None:
        path = Path(__file__).resolve().parent / "static" / filename
        if not path.is_file():
            self._json({"error": "Arquivo da galeria nao encontrado"}, HTTPStatus.NOT_FOUND)
            return
        body = path.read_bytes()
        self._headers(HTTPStatus.OK, content_type, len(body))
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802 - contrato de BaseHTTPRequestHandler
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"
        params = parse_qs(parsed.query)

        if path == f"{BASE_PATH}/health":
            ready = DB_PATH.is_file() and MEDIA_DIR.is_dir() and bool(SESSION_SECRET)
            self._json({"ok": ready}, HTTPStatus.OK if ready else HTTPStatus.SERVICE_UNAVAILABLE)
            return
        if path in (BASE_PATH, f"{BASE_PATH}/index.html"):
            self._serve_static("index.html", "text/html; charset=utf-8")
            return
        if path == f"{BASE_PATH}/app.css":
            self._serve_static("app.css", "text/css; charset=utf-8")
            return
        if path == f"{BASE_PATH}/app.js":
            self._serve_static("app.js", "application/javascript; charset=utf-8")
            return
        if path.startswith(f"{BASE_PATH}/media/"):
            relative = path[len(f"{BASE_PATH}/media/") :]
            if not _valid_media_signature(unquote(relative), params):
                self._unauthorized()
                return
            media = _safe_media_path(relative)
            if media is None:
                self._json({"error": "Imagem nao encontrada"}, HTTPStatus.NOT_FOUND)
                return
            content_type = mimetypes.guess_type(media.name)[0] or "application/octet-stream"
            self._headers(HTTPStatus.OK, content_type, media.stat().st_size)
            with media.open("rb") as source:
                while chunk := source.read(1024 * 1024):
                    self.wfile.write(chunk)
            return

        if not path.startswith(f"{BASE_PATH}/api/"):
            self._json({"error": "Rota nao encontrada"}, HTTPStatus.NOT_FOUND)
            return
        if not _valid_bearer(self.headers.get("Authorization")):
            self._unauthorized()
            return
        if not DB_PATH.is_file():
            self._json({"error": "Galeria ainda nao foi indexada"}, HTTPStatus.SERVICE_UNAVAILABLE)
            return

        if path == f"{BASE_PATH}/api/images":
            self._list_images(params)
            return
        if path == f"{BASE_PATH}/api/filters":
            self._filters()
            return
        match = re.fullmatch(re.escape(f"{BASE_PATH}/api/images/") + r"(\d+)/download", path)
        if match:
            self._download_image(int(match.group(1)))
            return
        self._json({"error": "Rota nao encontrada"}, HTTPStatus.NOT_FOUND)

    def _list_images(self, params: dict[str, list[str]]) -> None:
        try:
            page = max(1, int((params.get("page") or ["1"])[0]))
            limit = min(MAX_PAGE_SIZE, max(1, int((params.get("limit") or ["48"])[0])))
        except ValueError:
            self._json({"error": "Paginacao invalida"}, HTTPStatus.BAD_REQUEST)
            return
        q = (params.get("q") or [""])[0].strip()
        category = (params.get("category") or [""])[0].strip()
        subcategory = (params.get("subcategory") or [""])[0].strip()
        brand = (params.get("brand") or [""])[0].strip()
        orphan = (params.get("orphan") or [""])[0]

        joins = ""
        where: list[str] = []
        values: list[object] = []
        if q and _fts_query(q):
            joins = " JOIN images_fts ON images_fts.rowid=i.id"
            where.append("images_fts MATCH ?")
            values.append(_fts_query(q))
        if category:
            where.append("i.category=?")
            values.append(category)
        if subcategory:
            where.append("i.subcategory=?")
            values.append(subcategory)
        if brand:
            where.append("i.brand=?")
            values.append(brand)
        if orphan in ("0", "1"):
            where.append("i.orphan=?")
            values.append(int(orphan))
        clause = " WHERE " + " AND ".join(where) if where else ""
        offset = (page - 1) * limit
        with closing(_connect()) as conn:
            total = int(conn.execute(f"SELECT COUNT(*) FROM images i{joins}{clause}", values).fetchone()[0])
            rows = conn.execute(
                "SELECT i.id,i.legacy_product_id,i.legacy_image_id,i.product_name,i.category,"
                "i.subcategory,i.brand,i.relative_path,i.sha256,i.bytes,i.orphan "
                f"FROM images i{joins}{clause} ORDER BY i.product_name,i.id LIMIT ? OFFSET ?",
                [*values, limit, offset],
            ).fetchall()
        items = []
        for row in rows:
            item = dict(row)
            item["media_url"] = _signed_media_url(item["relative_path"])
            items.append(item)
        self._json({"items": items, "total": total, "page": page, "limit": limit})

    def _filters(self) -> None:
        with closing(_connect()) as conn:
            rows = conn.execute("SELECT kind,value,total FROM gallery_filters ORDER BY kind,value").fetchall()
        result = {"category": [], "subcategory": [], "brand": []}
        for row in rows:
            result[row["kind"]].append({"value": row["value"], "total": row["total"]})
        self._json(result)

    def _download_image(self, image_id: int) -> None:
        with closing(_connect()) as conn:
            row = conn.execute(
                "SELECT relative_path,sha256,bytes FROM images WHERE id=?", (image_id,)
            ).fetchone()
        if row is None:
            self._json({"error": "Imagem nao encontrada"}, HTTPStatus.NOT_FOUND)
            return
        media = _safe_media_path(row["relative_path"])
        if media is None:
            self._json({"error": "Arquivo da imagem nao encontrado"}, HTTPStatus.NOT_FOUND)
            return
        content_type = mimetypes.guess_type(media.name)[0] or "application/octet-stream"
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(media.stat().st_size))
        self.send_header("X-Image-SHA256", row["sha256"])
        self.send_header("Content-Disposition", f'attachment; filename="{media.name}"')
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        with media.open("rb") as source:
            while chunk := source.read(1024 * 1024):
                self.wfile.write(chunk)


def main() -> None:
    if not SESSION_SECRET:
        raise RuntimeError("GALLERY_SESSION_SECRET deve ser configurada")
    server = ThreadingHTTPServer((HOST, PORT), GalleryHandler)
    print(f"Galeria disponivel em http://{HOST}:{PORT}{BASE_PATH}/", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
