"""Exporta o catálogo do crawler (crawler.db) para JSON.

Formato consumido pelo ERP (`catalog_server.importar_catalogo`): cada produto
parseado vem com seus atributos estruturados (`product_attributes`) e imagens,
permitindo o agrupamento em famílias/variantes do lado do ERP.

Uso:
    python -m app.exporters.json_exporter [--saida output/catalogo.json]
"""
from __future__ import annotations

import argparse
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from app.config.settings import DATABASE_FOLDER, OUTPUT_FOLDER

FORMATO_VERSAO = 1


def _connect():
    path = DATABASE_FOLDER / "crawler.db"
    conn = sqlite3.connect(f"file:{path.resolve().as_posix()}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def export(conn=None) -> list[dict]:
    """Monta a lista de produtos (dict) com atributos e imagens embutidos."""
    close = conn is None
    conn = conn or _connect()
    try:
        attrs_map: dict[int, dict] = {}
        try:
            for r in conn.execute(
                "SELECT product_id, attr, value FROM product_attributes"
            ):
                attrs_map.setdefault(r["product_id"], {})[r["attr"]] = r["value"]
        except sqlite3.OperationalError:
            pass
        imgs_map: dict[int, list] = {}
        for r in conn.execute(
            "SELECT product_id, filename, url FROM images ORDER BY id"
        ):
            imgs_map.setdefault(r["product_id"], []).append(
                {"filename": r["filename"], "url": r["url"]}
            )

        produtos = []
        for r in conn.execute(
            "SELECT * FROM products WHERE parsed=1 ORDER BY id"
        ):
            d = dict(r)
            d["atributos"] = attrs_map.get(d["id"], {})
            d["imagens"] = imgs_map.get(d["id"], [])
            produtos.append(d)
        return produtos
    finally:
        if close:
            conn.close()


def exportar_arquivo(path: Path | None = None) -> Path:
    path = path or OUTPUT_FOLDER / "catalogo.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    dados = {
        "formato": FORMATO_VERSAO,
        "exportado_em": datetime.now(timezone.utc).isoformat(),
        "produtos": export(),
    }
    with open(path, "w", encoding="utf-8") as fp:
        json.dump(dados, fp, ensure_ascii=False, indent=2)
    return path


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Exporta o crawler.db para JSON")
    ap.add_argument("--saida", default=str(OUTPUT_FOLDER / "catalogo.json"))
    args = ap.parse_args()
    destino = exportar_arquivo(Path(args.saida))
    print(f"Exportação concluída: {destino}")
