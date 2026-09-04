from __future__ import annotations

import base64
import hashlib
import hmac
import importlib.util
import json
import os
import sqlite3
import tempfile
import threading
import time
import unittest
import urllib.request
from contextlib import closing
from pathlib import Path


class GalleryHttpTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        data = Path(self.temp.name)
        media = data / "media" / "ELE" / "CAB"
        media.mkdir(parents=True)
        image = media / "produto.jpg"
        image.write_bytes(b"imagem-http")
        digest = hashlib.sha256(image.read_bytes()).hexdigest()
        with closing(sqlite3.connect(data / "gallery.sqlite3")) as conn:
            conn.executescript(
                """
                CREATE TABLE images (
                    id INTEGER PRIMARY KEY, legacy_product_id INTEGER,
                    legacy_image_id INTEGER, product_name TEXT, category TEXT,
                    subcategory TEXT, brand TEXT, relative_path TEXT,
                    sha256 TEXT, bytes INTEGER, orphan INTEGER, search_text TEXT
                );
                CREATE TABLE gallery_filters (
                    kind TEXT, value TEXT, total INTEGER, PRIMARY KEY(kind,value)
                );
                CREATE VIRTUAL TABLE images_fts USING fts5(
                    search_text, content='images', content_rowid='id'
                );
                """
            )
            conn.execute(
                "INSERT INTO images VALUES (1,10,20,'Cabo Flexivel','Eletrica','Cabos',"
                "'Sil','ELE/CAB/produto.jpg',?,?,0,'Cabo Flexivel Eletrica Cabos Sil')",
                (digest, image.stat().st_size),
            )
            conn.execute("INSERT INTO images_fts(rowid,search_text) SELECT id,search_text FROM images")
            conn.execute("INSERT INTO gallery_filters VALUES ('category','Eletrica',1)")
            conn.commit()

        os.environ["GALLERY_DATA_DIR"] = str(data)
        os.environ["GALLERY_SESSION_SECRET"] = "segredo-de-teste"
        os.environ["GALLERY_BASE_PATH"] = "/galeria"
        module_path = Path(__file__).with_name("app.py")
        spec = importlib.util.spec_from_file_location("gallery_app_test", module_path)
        self.app = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(self.app)
        self.server = self.app.ThreadingHTTPServer(("127.0.0.1", 0), self.app.GalleryHandler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base = f"http://127.0.0.1:{self.server.server_port}/galeria"

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)
        self.temp.cleanup()

    def _session(self):
        payload = base64.urlsafe_b64encode(
            json.dumps({"uid": 1, "exp": int(time.time()) + 60}).encode()
        ).decode().rstrip("=")
        signature = hmac.new(b"segredo-de-teste", payload.encode(), hashlib.sha256).hexdigest()
        return f"{payload}.{signature}"

    def _json(self, path):
        request = urllib.request.Request(
            self.base + path, headers={"Authorization": f"Bearer {self._session()}"}
        )
        with urllib.request.urlopen(request, timeout=3) as response:
            return json.load(response)

    def test_health_search_filters_and_download(self):
        with urllib.request.urlopen(self.base + "/health", timeout=3) as response:
            self.assertTrue(json.load(response)["ok"])
        self.assertEqual(self._json("/api/filters")["category"][0]["value"], "Eletrica")
        result = self._json("/api/images?q=cabo")
        self.assertEqual(result["total"], 1)
        with urllib.request.urlopen("http://127.0.0.1:" + str(self.server.server_port) + result["items"][0]["media_url"]) as response:
            self.assertEqual(response.read(), b"imagem-http")

        service = hmac.new(
            b"segredo-de-teste", b"siscom-gallery-service", hashlib.sha256
        ).hexdigest()
        request = urllib.request.Request(
            self.base + "/api/images/1/download",
            headers={"Authorization": f"Bearer {service}"},
        )
        with urllib.request.urlopen(request, timeout=3) as response:
            self.assertEqual(response.read(), b"imagem-http")


if __name__ == "__main__":
    unittest.main()
