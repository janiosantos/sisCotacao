"""Crawler multi-site com pool de threads (Fbits e afins).

Descobre os produtos de cada site pelo sitemap.xml e baixa os pendentes em
paralelo: usa um `ThreadPoolExecutor` para processar vários produtos ao mesmo
tempo e as URLs de TODOS os sites selecionados entram numa mesma fila — ou
seja, os sites são processados em paralelo entre si também.

Para cada URL usa o mesmo fluxo do botão "Novo via URL"
(`parse_url_service.criar_produto_por_url`), incluindo o fix de URLs com
caracteres não-ASCII e os downloads de imagem fora da transação do SQLite.

Uso:
    python crawl_sites.py                                          # casamattos + anhanguera, 8 workers
    python crawl_sites.py --sites casamattos,anhanguera            # idem (explícito)
    python crawl_sites.py --sites casamattos --workers 12 --limit 100
    python crawl_sites.py --sites anhanguera --count               # só conta os pendentes
    python crawl_sites.py --delay 0.3                              # pausa por worker (s)
"""
from __future__ import annotations

import argparse
import logging
import re
import sqlite3
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from catalog_server.config import SYSTEM_DB
from catalog_server.services import parse_url_service

SITES: dict[str, dict] = {
    "casadosparafusos": {
        "sitemap": "https://www.casadosparafusos.com/sitemap.xml",
        "filter": "/produto/",
        "log": "crawl_casadosparafusos.log",
    },
    "casamattos": {
        "sitemap": "https://www.casamattos.com.br/sitemap.xml",
        "filter": "/produto/",
        "log": "crawl_casamattos.log",
    },
    "anhanguera": {
        "sitemap": "https://www.anhangueraferramentas.com.br/sitemap.xml",
        "filter": "/produto/",
        "log": "crawl_anhanguera.log",
    },
}

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/138.0 Safari/537.36"
)

_LOG_DIR = ROOT / "logs"


def _session() -> requests.Session:
    sess = requests.Session()
    sess.headers.update({"User-Agent": UA, "Accept-Language": "pt-BR,pt;q=0.9"})
    return sess


def _urls_do_sitemap(sess: requests.Session, url: str, visited: set | None = None) -> list[str]:
    """Baixa o sitemap (suporta sitemap index e urlset aninhado)."""
    if visited is None:
        visited = set()
    if url in visited:
        return []
    visited.add(url)

    resp = sess.get(url, timeout=120)
    resp.raise_for_status()
    text = resp.text

    if "<sitemapindex" in text.lower():
        out: list[str] = []
        for child in re.findall(r"<loc>(.*?)</loc>", text):
            out.extend(_urls_do_sitemap(sess, child.strip(), visited))
        return out

    return [u.strip() for u in re.findall(r"<loc>(.*?)</loc>", text)]


def descobrir_produtos(sess: requests.Session, site: dict) -> list[str]:
    urls = _urls_do_sitemap(sess, site["sitemap"])
    filtro = site.get("filter", "/produto/")
    return sorted({u for u in urls if filtro in u})


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


class Stats:
    """Contadores de progresso (thread-safe)."""

    def __init__(self):
        self.lock = threading.Lock()
        self.total = 0
        self.processados = 0
        self.ok = 0
        self.falhas = 0
        self.por_site: dict[str, list[int]] = {}

    def add(self, site: str, ok: bool) -> None:
        with self.lock:
            self.processados += 1
            if ok:
                self.ok += 1
            else:
                self.falhas += 1
            d = self.por_site.setdefault(site, [0, 0])
            d[0 if ok else 1] += 1


def _processar(log: logging.Logger, stats: Stats, site: str, url: str, delay: float) -> None:
    # Uma única tentativa extra cobre falhas transitórias (throttle/anti-bot e
    # "database is locked" sob concorrência) sem transformar erro persistente
    # de parsing em loop.
    ultimo: Exception | None = None
    for tentativa in (1, 2):
        try:
            criado = parse_url_service.criar_produto_por_url(url)
            stats.add(site, True)
            log.info(
                "[OK] id=%s fotos=%s | %s",
                criado["id"], criado["imagens_baixadas"], url,
            )
            if delay:
                time.sleep(delay)
            return
        except Exception as exc:  # noqa: BLE001 — um erro não deve parar o lote
            ultimo = exc
            time.sleep(2 * tentativa)
    stats.add(site, False)
    log.warning("[FALHA] %s | %s", url, ultimo)


def _progress_thread(stats: Stats, stop: threading.Event) -> None:
    while not stop.is_set():
        stop.wait(30)
        if stop.is_set():
            break
        com = stats.processados or 1
        resto = stats.total - stats.processados
        eta = resto * (time.time() - _t0) / com / 60 if com > 0 else 0
        print(
            f"[progresso] {stats.processados}/{stats.total} "
            f"(ok={stats.ok} falhas={stats.falhas}) ETA ~{eta:.0f} min"
        )
        for site, (ok, falhas) in sorted(stats.por_site.items()):
            print(f"    {site}: ok={ok} falhas={falhas}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Crawler multi-site com pool de threads")
    parser.add_argument(
        "--sites", default="casamattos,anhanguera",
        help="Sites a processar, separados por vírgula (padrão: casamattos,anhanguera)",
    )
    parser.add_argument("--workers", type=int, default=8, help="Threads simultâneas (padrão: 8)")
    parser.add_argument("--limit", type=int, default=0, help="Máximo de produtos a baixar (0 = todos)")
    parser.add_argument("--offset", type=int, default=0, help="Pula os N primeiros pendentes")
    parser.add_argument("--delay", type=float, default=0.3, help="Pausa por worker após cada produto (s)")
    parser.add_argument("--count", action="store_true", help="Só mostra quantos estão pendentes")
    args = parser.parse_args()

    nomes = [n.strip() for n in args.sites.split(",") if n.strip()]
    desconhecidos = [n for n in nomes if n not in SITES]
    if desconhecidos:
        sys.exit(f"Site(s) desconhecido(s): {', '.join(desconhecidos)}. Disponíveis: {', '.join(SITES)}")

    _LOG_DIR.mkdir(parents=True, exist_ok=True)

    loggers = {}
    for nome in nomes:
        lg = logging.getLogger(f"crawl_{nome}")
        lg.setLevel(logging.INFO)
        lg.handlers.clear()
        fmt = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
        fh = logging.FileHandler(_LOG_DIR / SITES[nome]["log"], encoding="utf-8")
        fh.setFormatter(fmt)
        lg.addHandler(fh)
        loggers[nome] = lg

    sess = _session()

    pendentes_por_site: dict[str, list[str]] = {}
    for nome in nomes:
        site = SITES[nome]
        loggers[nome].info("Buscando sitemap em %s", site["sitemap"])
        try:
            prods = descobrir_produtos(sess, site)
        except requests.RequestException as exc:
            loggers[nome].error("Não foi possível obter o sitemap: %s", exc)
            sys.exit(1)
        cadastrados = carregar_cadastrados()
        pend = [u for u in prods if u not in cadastrados]
        loggers[nome].info(
            "Sitemap: %d | já cadastrados: %d | pendentes: %d",
            len(prods), len(prods) - len(pend), len(pend),
        )
        pendentes_por_site[nome] = pend

    total_pend = sum(len(v) for v in pendentes_por_site.values())
    print(f"Total de pendentes: {total_pend}")
    for nome in nomes:
        print(f"  {nome}: {len(pendentes_por_site[nome])}")

    if args.count:
        return

    fila: list[tuple[str, str]] = []
    # Intercala os sites para que --limit/--offset abranjam todos (e não só o 1º).
    max_len = max(len(pendentes_por_site[n]) for n in nomes)
    for i in range(max_len):
        for nome in nomes:
            pend = pendentes_por_site[nome]
            if i < len(pend):
                fila.append((nome, pend[i]))
    if args.offset:
        fila = fila[args.offset:]
    if args.limit:
        fila = fila[: args.limit]

    if not fila:
        print("Nada a fazer — nenhum produto pendente.")
        return

    stats = Stats()
    stats.total = len(fila)

    global _t0
    _t0 = time.time()
    stop = threading.Event()
    if fila and len(fila) > 5:
        threading.Thread(target=_progress_thread, args=(stats, stop), daemon=True).start()

    print(f"Iniciando com {args.workers} workers e {len(fila)} produto(s)...")
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = [
            pool.submit(_processar, loggers[site], stats, site, url, args.delay)
            for site, url in fila
        ]
        for _ in as_completed(futures):
            pass

    stop.set()
    elapsed = time.time() - _t0
    print(
        f"Concluído: {stats.ok} criados, {stats.falhas} falhas em {elapsed / 60:.1f} min"
    )
    for nome in nomes:
        ok, falhas = stats.por_site.get(nome, [0, 0])
        loggers[nome].info(
            "Concluído: %d criados, %d falhas em %.1f min", ok, falhas, elapsed / 60,
        )


_t0 = 0.0


if __name__ == "__main__":
    main()
