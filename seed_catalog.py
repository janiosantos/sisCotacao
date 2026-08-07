"""Popula o Qdrant (via microserviço Cotações IA Importer) com o catálogo real.

Lê as variantes ativas do `catalog_server/data/server.db` (mesma base usada
pelo catálogo e pelas cotações) e envia em lotes para `POST /api/catalog/seed`.

Uso:
  python seed_catalog.py                        # catálogo completo (reset na 1ª leva)
  python seed_catalog.py --limit 5000           # só as 5.000 primeiras variantes
  python seed_catalog.py --url http://host:8001 --chunk 1000 --reset-first

O progresso vai para stdout e para `seed_catalog.log`.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

SERVER_DB = Path(__file__).resolve().parent / "catalog_server" / "data" / "server.db"

SQL_VARIANTES = """
    SELECT v.id, p.nome
    FROM variantes v
    JOIN produtos_cadastro p ON p.id = v.produto_id
    WHERE v.ativo = 1
    ORDER BY v.id
"""

LOG: Path = Path(__file__).resolve().parent / "seed_catalog.log"


def info(msg: str) -> None:
    line = f"[{time.strftime('%H:%M:%S')}] {msg}"
    print(line, flush=True)
    with LOG.open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def post(url: str, payload: dict) -> dict:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        url, data=body, headers={"Content-Type": "application/json"}, method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=7200) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"microserviço respondeu HTTP {exc.code}: {exc.read().decode()[:300]}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"não acessei o microserviço ({url}): {exc.reason}") from exc


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--limit", type=int, default=0, help="0 = todas as variantes")
    ap.add_argument("--chunk", type=int, default=2000)
    ap.add_argument("--url", default="http://127.0.0.1:8001", help="API do microserviço")
    ap.add_argument("--reset-first", action="store_true", default=True,
                    help="recria a collection na 1ª leva (padrão)")
    args = ap.parse_args()

    sql = SQL_VARIANTES + (f" LIMIT {int(args.limit)}" if args.limit > 0 else "")
    conn = sqlite3.connect(f"file:{SERVER_DB}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row

    inicio = time.time()
    try:
        refs = conn.execute(sql).fetchall()
    finally:
        conn.close()

    produtos = [{"id": r["id"], "name": r["nome"]} for r in refs if r["nome"]]
    total = len(produtos)
    if not total:
        info("nenhuma variante ativa no catálogo; nada a fazer.")
        return 1

    info(f"catálogo real: {total} variantes — enviando em lotes de {args.chunk}")

    for offset in range(0, total, args.chunk):
        fatia = produtos[offset: offset + args.chunk]
        reset = args.reset_first and offset == 0
        try:
            resp = post(args.url.rstrip("/") + "/api/catalog/seed", {"produtos": fatia, "reset": reset})
        except RuntimeError as exc:
            info(f"ERRO no lote {offset//args.chunk + 1} ({offset}-{offset + len(fatia)}): {exc}")
            return 2
        info(
            f"lote {(offset // args.chunk) + 1} ({offset + 1}..{offset + len(fatia)} de {total}): "
            f"populados={resp.get('populados')} | {int(time.time() - inicio)}s"
        )

    info(f"DONE: {total} produtos indexados em {int(time.time() - inicio)}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())