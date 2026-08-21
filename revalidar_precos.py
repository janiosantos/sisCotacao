"""Revalida (corrige) preços das variantes suspeitas consultando a URL de origem.

Usa o parser de produto (já corrigido para capturar o preço do PRÓPRIO produto,
e não o de um "relacionado") para re-baixar cada página e atualizar `preco`,
`pix_price`, `old_price` e `installment` com o valor atual da loja.

Alvos = variantes dos grupos apontados pelo `detect_anomalias.py` (mesmo EAN
ou mesma bitola com razão de preço >= limite).

Uso:
    python revalidar_precos.py                     # revalida todos os suspeitos
    python revalidar_precos.py --ratio 1.5 --workers 8
    python revalidar_precos.py --dry               # não grava nada
    python revalidar_precos.py --limit 20          # só os 20 primeiros (teste)
"""
from __future__ import annotations

import argparse
import logging
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from catalog_server.config import DATABASE_URL  # noqa: E402
from catalog_server.db import system_conn  # noqa: E402
from catalog_server.services import parse_url_service  # noqa: E402
from detect_anomalias import bitola_no_produto, ean_duplicatas  # noqa: E402

_LOG_DIR = ROOT / "logs"
_LOG = _LOG_DIR / "revalidar_precos.log"


def _backup() -> str:
    return "Postgres (backup não se aplica a arquivo)"


def _alvos(conn: Any, ratio: float) -> set[int]:
    alvos: set[int] = set()
    for grupo in ean_duplicatas(conn, ratio) + bitola_no_produto(conn, ratio):
        if not grupo["anomalia"]:
            continue
        for it in grupo["itens"]:
            alvos.add(it["variante_id"])
    return alvos


class Stats:
    def __init__(self):
        self.lock = threading.Lock()
        self.total = 0
        self.ok = 0
        self.erros = 0
        self.sem_preco = 0
        self.t_ini = time.time()
        self._qtd_por_worker = 0

    def progress(self):
        with self.lock:
            return self.total, (self.ok + self.erros + self.sem_preco)


def _processar(valor_id: int, url: str, apply: bool) -> tuple[int, str | None, float | None]:
    try:
        data = parse_url_service.parse_url(url)
        price = data.get("price")
        if not price or price <= 0:
            return valor_id, "sem_preco", None
        if apply:
            pix = data.get("pix_price") or price
            old = data.get("old_price")
            inst = data.get("installment") or ""
            with system_conn() as conn2:
                conn2.execute(
                    "UPDATE variantes SET preco=?, preco_promocional=?, old_price=?, pix_price=?, installment=? WHERE id=?",
                    (round(price, 2), round(pix, 2), old, round(pix, 2), inst, valor_id),
                )
        return valor_id, "ok", price
    except Exception as exc:  # noqa: BLE001
        return valor_id, f"erro:{type(exc).__name__}:{exc}", None


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ratio", type=float, default=1.5)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--offset", type=int, default=0)
    ap.add_argument("--dry", action="store_true", help="não grava nada (só verifica)")
    args = ap.parse_args()

    with system_conn() as conn:
        ids = _alvos(conn, args.ratio)
        if not ids:
            print("Nenhuma variante suspeita.")
            return
        placeholders = ",".join("?" * len(ids))
        rows = [
            dict(r)
            for r in conn.execute(
                f"""SELECT v.id, v.url, v.sku FROM variantes v
                    WHERE v.id IN ({placeholders}) AND v.url <> ''""",
                list(ids),
            )
        ]

    alvos = rows
    sem_url = len(ids) - len(alvos)
    if args.offset:
        alvos = alvos[args.offset:]
    if args.limit:
        alvos = alvos[: args.limit]
    if not alvos:
        print("Nada para revalidar.")
        return

    backup = _backup() if not args.dry else "—"
    print(f"Backup: {backup}")
    print(f"Alvos: {len(alvos)} de {len(ids)} variantes suspeitas ({sem_url} sem URL)")
    print(f"Modo: {'DRY-RUN (nada será gravado)' if args.dry else 'APLICANDO updates'}")
    print(f"Iniciando com {args.workers} workers ({len(alvos)} itens)...")

    _LOG_DIR.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        filename=_LOG.as_posix(), level=logging.INFO,
        format="%(asctime)s %(message)s", encoding="utf-8", filemode="w",
    )
    log = logging.getLogger("revalidate")

    resultados: dict[str, int] = {"ok": 0, "sem_preco": 0, "erro": 0}
    mudancas: list[tuple] = []
    t0 = time.time()
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        fut = {pool.submit(_processar, a["id"], a["url"], not args.dry): a for a in alvos}
        n = 0
        for f in as_completed(fut):
            n += 1
            vid, status, price = f.result()
            a = fut[f]
            if status == "ok":
                resultados["ok"] += 1
            elif status == "sem_preco":
                resultados["sem_preco"] += 1
            else:
                resultados["erro"] += 1
                log.warning("[erro] var %s %s | %s", vid, status, a["url"])
            if status == "ok":
                mudancas.append((vid, a["sku"], price, a["url"]))
            if n % 25 == 0 or n == len(fut):
                et = (time.time() - t0) / 60
                print(f"  {n}/{len(alvos)}  ok={resultados['ok']} sem_preco={resultados['sem_preco']} erro={resultados['erro']} ({et:.1f} min)")

    print("\nConcluído em %.1f min" % ((time.time() - t0) / 60))
    print("Resumo:", resultados)
    if not args.dry and mudancas:
        csv_path = ROOT / f"precos_revalidados_{datetime.now():%Y%m%d_%H%M%S}.csv"
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            import csv
            w = csv.writer(f)
            w.writerow(["variante_id", "sku", "preco", "url"])
            w.writerows(mudancas)
        print(f"Alterações gravadas em: {csv_path}")


if __name__ == "__main__":
    main()