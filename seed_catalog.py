"""Popula o Qdrant (via microserviço Cotações IA Importer) com o catálogo real.

Lê as variantes ativas do banco PostgreSQL do ERP (mesma base usada pelo
catálogo e pelas cotações) e envia em lotes para `POST /api/catalog/seed`.

Uso:
  python seed_catalog.py                        # catálogo completo (reset na 1ª leva)
  python seed_catalog.py --limit 5000           # só as 5.000 primeiras variantes
  python seed_catalog.py --url http://host:8001 --chunk 1000 --reset-first

O progresso vai para stdout e para `seed_catalog.log`.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from catalog_server.db import system_conn

# Variantes ativas + campos para montar o texto enriquecido de cada item.
SQL_VARIANTES = """
    SELECT v.id, p.nome, p.familia_id, p.embalagem,
           NULLIF(COALESCE(NULLIF(TRIM(v.marca), ''), NULLIF(TRIM(p.marca), '')), '') AS marca
    FROM variantes v
    JOIN produtos_cadastro p ON p.id = v.produto_id
    WHERE v.ativo = 1
    ORDER BY v.id
"""

# Atributos de cada variante (cor, bitola, embalagem…) já na ordem de exibição.
SQL_ATRIBUTOS = """
    SELECT va.variante_id, fa.nome, va.valor
    FROM variante_atributos va
    JOIN familia_atributos fa ON fa.id = va.atributo_id
    WHERE va.valor IS NOT NULL AND TRIM(va.valor) <> ''
    ORDER BY va.variante_id, fa.ordem
"""

LOG: Path = ROOT / "seed_catalog.log"


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


def montar_descricao(itens: list[Any], atributos: list[Any]) -> list[dict]:
    """Constrói o texto rico de cada variante: nome base + marca + embalagem +
    atributos (cor, bitola…), p/ o embed identificar a variante exata."""
    attrs: dict[int, list[str]] = {}
    parts: dict[int, list[str]] = {}
    for a in atributos:
        attrs.setdefault(a["variante_id"], []).append((a["nome"], a["valor"]))

    texto: list[dict] = []
    for r in itens:
        n = r["nome"]
        pedacos: list[str] = []
        if r["marca"]:
            pedacos.append(f"marca {r['marca']}")
        if r["embalagem"]:
            pedacos.append(f"embalagem {r['embalagem']}")
        for nome_attr, valor in attrs.get(r["id"], []):
            pedacos.append(f"{nome_attr}: {valor}")
        descricao = n
        if pedacos:
            descricao += " · " + " · ".join(pedacos)
        texto.append({"id": r["id"], "name": descricao, "base": n})
    return texto


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--limit", type=int, default=0, help="0 = todas as variantes")
    ap.add_argument("--chunk", type=int, default=2000)
    ap.add_argument("--url", default="http://127.0.0.1:8001", help="API do microserviço")
    ap.add_argument("--reset-first", action="store_true", default=True,
                    help="recria a collection na 1ª leva (padrão)")
    args = ap.parse_args()

    sql = SQL_VARIANTES + (f" LIMIT {int(args.limit)}" if args.limit > 0 else "")
    with system_conn() as conn:
        itens = list(conn.execute(sql))
        atributos = list(conn.execute(SQL_ATRIBUTOS))

    produtos = montar_descricao(itens, atributos)
    total = len(produtos)
    if not total:
        info("nenhuma variante ativa no catálogo; nada a fazer.")
        return 1

    info(f"catálogo real: {total} variantes — enviando em lotes de {args.chunk}")
    info("exemplo: " + produtos[0]["name"])

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