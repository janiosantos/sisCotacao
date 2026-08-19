"""Classifica (backfill) categoria/subcategoria dos produtos do catálogo.

Estratégia (conforme definido):
  1. Breadcrumb da loja na página do produto (anhanguera/casadosparafusos/
     casadoeletricistasc) — requer baixar 1 URL por produto.
  2. Fallback por palavras-chave no nome/marca (casamattos e onde o breadcrumb
     falhar) — offline.

Categoria = caminho completo ("A > B > C"); subcategoria = último nível.

Uso:
    python classificar_produtos.py                     # classifica todos (sem categoria)
    python classificar_produtos.py --dry               # não grava nada
    python classificar_produtos.py --workers 12
    python classificar_produtos.py --only-offline      # só fallback por nome (sem rede)
    python classificar_produtos.py --only-online
    python classificar_produtos.py --limit 50          # teste
"""
from __future__ import annotations

import argparse
import csv
import logging
import shutil
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from catalog_server import classification as C  # noqa: E402
from catalog_server import categorias  # noqa: E402
from catalog_server.config import DATABASE_URL  # noqa: E402
from catalog_server.db import SYSTEM_DB, system_conn  # noqa: E402
from catalog_server.services import parse_url_service  # noqa: E402
from catalog_server import source_cache  # noqa: E402

DB = Path(SYSTEM_DB)
_IS_PG = bool(DATABASE_URL)
_LOG_DIR = ROOT / "logs"

_SEM_BREADCRUMB = ("casamattos",)
_ONLINE_HOSTS = ("anhangueraferramentas", "casadosparafusos", "casadoeletricistascas")


def _backup() -> str:
    if _IS_PG:
        return "Postgres (backup não se aplica a arquivo)"
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    dest = DB.with_name(f"server_backup_classificar_{ts}.db")
    shutil.copy2(DB, dest)
    return str(dest)


def _host(url: str) -> str:
    return (urlparse(url).hostname or "").lower()


def _precisa_rede(url: str) -> bool:
    return any(h in _host(url) for h in _ONLINE_HOSTS)


def _classifica_offline(nome: str, marca: str) -> tuple[str, str]:
    items = C.fallback_categoria(nome, marca)
    return C.categoria(items), C.subcategoria(items)


def _processar(pro: dict, apply: bool):
    """Baixa a página, extrai breadcrumb e grava categoria/subcategoria."""
    url = pro["url"]
    try:
        if _precisa_rede(url):
            html, _ = parse_url_service._fetch_html(url)
            items = C.extract_breadcrumb(html, url, pro["nome"] or "")
            if not items:
                items = C.fallback_categoria(pro["nome"] or "", pro["marca"] or "")
        else:
            items = C.fallback_categoria(pro["nome"] or "", pro["marca"] or "")
    except Exception as exc:  # noqa: BLE001
        return pro["id"], f"erro:{type(exc).__name__}:{exc}", "", "", url

    cat = C.categoria(items)
    sub = C.subcategoria(items)
    source_cache.referenciar(url, produto_id=pro["id"])
    if not cat:
        return pro["id"], "sem_classificacao", "", "", url
    if apply:
        with system_conn() as conn:
            categoria_id, subcategoria_id = categorias.resolve(conn, cat, sub)
            conn.execute(
                "UPDATE produtos_cadastro SET categoria_id=?, subcategoria_id=?,"
                " atualizado_em=datetime('now') WHERE id=?",
                (categoria_id, subcategoria_id, pro["id"]),
            )
    return pro["id"], "ok", cat, sub, url


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--offset", type=int, default=0)
    ap.add_argument("--dry", action="store_true")
    ap.add_argument("--only-offline", action="store_true")
    ap.add_argument("--only-online", action="store_true")
    args = ap.parse_args()

    rows: list[dict] = []
    with system_conn() as conn:
        for r in conn.execute(
            """SELECT p.id, p.nome, p.marca,
                      (SELECT v.url FROM variantes v
                        WHERE v.produto_id = p.id AND v.url <> '' LIMIT 1) AS url
               FROM produtos_cadastro p
               WHERE p.categoria_id IS NULL
               ORDER BY p.id"""
        ):
            rows.append(dict(r))

    pros = rows
    offline = [p for p in pros if not _precisa_rede(p["url"] or "")]
    online = [p for p in pros if _precisa_rede(p["url"] or "")]
    if args.only_offline:
        alvo = offline
    elif args.only_online:
        alvo = online
    else:
        alvo = offline + online
    if args.offset:
        alvo = alvo[args.offset:]
    if args.limit:
        alvo = alvo[: args.limit]

    print(f"Total sem categoria: {len(pros)} | offline={len(offline)} online={len(online)}")
    print(f"Alvo nesta execução: {len(alvo)} | modo: {'DRY-RUN' if args.dry else 'APLICANDO'}")
    if not alvo:
        print("Nada a fazer.")
        return

    backup = _backup() if not args.dry else "—"
    print(f"Backup: {backup}")

    _LOG_DIR.mkdir(parents=True, exist_ok=True)
    logpath = _LOG_DIR / f"classificar_{datetime.now():%Y%m%d_%H%M%S}.log"
    logging.basicConfig(filename=str(logpath), level=logging.INFO,
                        format="%(asctime)s %(message)s", encoding="utf-8", filemode="w")
    log = logging.getLogger("classify")

    res = {"ok": 0, "sem_classificacao": 0, "erro": 0}
    t0 = time.time()
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        fut = {pool.submit(_processar, p, not args.dry): p for p in alvo}
        for i, f in enumerate(as_completed(fut), 1):
            pid, status, cat, sub, url = f.result()
            if status == "ok":
                res["ok"] += 1
            elif status == "sem_classificacao":
                res["sem_classificacao"] += 1
            else:
                res["erro"] += 1
                log.warning("[erro] produto %s | %s", pid, status)
            if i % 50 == 0 or i == len(fut):
                et = (time.time() - t0) / 60
                print(f"  {i}/{len(alvo)}  ok={res['ok']} sem={res['sem_classificacao']} "
                      f"erro={res['erro']} ({et:.1f} min)", flush=True)

    print("\nConcluído em %.1f min" % ((time.time() - t0) / 60))
    print("Resumo:", res)
    print("Log:", logpath)


if __name__ == "__main__":
    main()