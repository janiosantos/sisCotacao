from __future__ import annotations

import json
import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path

from deployment.galeria_produtos.relink import relink


class RelinkTest(unittest.TestCase):
    def test_substitui_copia_por_hardlink(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            images = root / "siscom" / "img"
            gallery = root / "galeria" / "data"
            source = images / "cadastro" / "1" / "foto.jpg"
            target = gallery / "media" / "ELE" / "CAB" / "foto.jpg"
            source.parent.mkdir(parents=True)
            target.parent.mkdir(parents=True)
            source.write_bytes(b"imagem")
            target.write_bytes(b"imagem")
            with closing(sqlite3.connect(gallery / "gallery.sqlite3")) as conn:
                conn.execute(
                    "CREATE TABLE images "
                    "(id INTEGER,source_path TEXT,relative_path TEXT,bytes INTEGER)"
                )
                conn.execute(
                    "INSERT INTO images VALUES (1,?,?,?)",
                    ("cadastro/1/foto.jpg", "ELE/CAB/foto.jpg", 6),
                )
                conn.commit()
            (gallery / "manifest.json").write_text(
                json.dumps({"hardlinks": 0, "copies": 1}), encoding="utf-8"
            )

            result = relink(images, gallery)

            self.assertEqual(result["linked"], 1)
            self.assertTrue(source.samefile(target))
            manifest = json.loads((gallery / "manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["hardlinks"], 1)
            self.assertEqual(manifest["copies"], 0)


if __name__ == "__main__":
    unittest.main()
