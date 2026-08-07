"""Baixa todo o catálogo da Casa dos Parafusos e cadastra no banco unificado.

Descobre os produtos pelo sitemap.xml e, para cada produto ainda não
cadastrado (verificado por URL em `produtos_cadastro`), baixa a página,
extrai os dados e cria família/produto/variação/atributos/fotos no `server.db`
— o mesmo fluxo do botão "Novo via URL" do catálogo.

Uso:
    python crawl_casadosparafusos.py               # baixa tudo
    python crawl_casadosparafusos.py --limit 50    # só os 50 primeiros pendentes
    python crawl_casadosparafusos.py --offset 200  # pula os 200 primeiros
    python crawl_casadosparafusos.py --count       # só conta os pendentes
    python crawl_casadosparafusos.py --delay 0.8   # pausa entre requisições (s)
"""
from __future__ import annotations

import argparse
import logging
import re
import sqlite3
import sys
import time
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from catalog_server.config import SYSTEM_DB
from catalog_server.services import parse_url_service

BASE = "https://www.casadosparafusos.com"
SITEMAP = f"{BASE}/sitemap.xml"

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/138.0 Safari/537.36"
)

_LOG_DIR = ROOT / "logs"


def _session() -> requests.Session:
    sess = requests.Session()
    sess.headers.update({"User-Agent": UA, "Accept-Language": "pt-BR,pt;q=0.9"})
    return sess


def listar_produtos(sess: requests.Session) -> list[str]:
    """Lê o sitemap e devolve todas as URLs de produto, ordenadas e sem duplicatas."""
    resp = sess.get(SITEMAP, timeout=120)
    resp.raise_for_status()
    urls = re.findall(r"<loc>(.*?)</loc>", resp.text)
    return sorted({u.strip() for u in urls if "/produto/" in u})


def carregar_cadastrados() -> set[str]:
    """Urls de produtos já cadastrados no server.db (produto ou variação)."""
    conn = sqlite3.connect(f"file:{SYSTEM_DB.as_posix()}?mode=ro", uri=True, timeout=10)
    conn.row_factory = sqlite3.Row
    try:
        urls = {r["url"] for r in conn.execute("SELECT url FROM produtos_cadastro WHERE url <> ''")}
        urls |= {r["url"] for r in conn.execute("SELECT url FROM variantes WHERE url <> ''")}
        return urls
    except sqlite3.OperationalError:
        return set()
    finally:
        conn.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Crawler da Casa dos Parafusos")
    parser.add_argument("--limit", type=int, default=0, help="Máximo de produtos a baixar (0 = todos)")
    parser.add_argument("--offset", type=int, default=0, help="Pula os N primeiros pendentes")
    parser.add_argument("--delay", type=float, default=0.6, help="Pausa entre produtos (segundos)")
    parser.add_argument("--count", action="store_true", help="Só mostra quantos estão pendentes")
    args = parser.parse_args()

    _LOG_DIR.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(_LOG_DIR / "crawl_casadosparafusos.log", encoding="utf-8"),
        ],
    )
    log = logging.getLogger("crawl")

    sess = _session()

    log.info("Buscando sitemap em %s", SITEMAP)
    try:
        prods = listar_produtos(sess)
    except requests.RequestException as exc:
        log.error("Não foi possível obter o sitemap: %s", exc)
        sys.exit(1)

    log.info("Total de produtos no sitemap: %d", len(prods))

    cadastrados = carregar_cadastrados()
    pendentes = [u for u in prods if u not in cadastrados]
    log.info("Já cadastrados: %d | pendentes: %d", len(prods) - len(pendentes), len(pendentes))

    if args.count:
        print(len(pendentes))
        return

    if args.offset:
        pendentes = pendentes[args.offset:]
    if args.limit:
        pendentes = pendentes[: args.limit]

    log.info("Iniciando baixa de %d produto(s)...", len(pendentes))
    ok = falhas = 0
    t0 = time.time()
    for i, url in enumerate(pendentes, 1):
        try:
            criado = parse_url_service.criar_produto_por_url(url)
            ok += 1
            log.info(
                "[%d/%d] OK id=%s fotos=%s | %s",
                i, len(pendentes), criado["id"], criado["imagens_baixadas"], url,
            )
        except Exception as exc:  # noqa: BLE001 — um erro não deve parar o lote
            falhas += 1
            log.warning("[%d/%d] FALHA | %s | %s", i, len(pendentes), url, exc)
        if i < len(pendentes):
            time.sleep(args.delay)

    elapsed = time.time() - t0
    log.info(
        "Concluído: %d criados, %d falhas em %.1f min",
        ok, falhas, elapsed / 60,
    )


if __name__ == "__main__":
    main()
