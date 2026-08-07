"""Move o cache de páginas-fonte (paginas_fonte) para um banco dedicado.

O HTML cru inflou o server.db (de ~117 MB para ~8 GB). Este script:
  1) copia todas as linhas de `paginas_fonte` para server_cache.db;
  2) remove a tabela `paginas_fonte` (e índices) do server.db;
  3) roda VACUUM no server.db para recuperar os ~8 GB de arquivo;
  4) deixa o cache disponível em server_cache.db (com backup do arquivo antigo).

Uso:
    python mover_cache_db.py            # aplica definitivo
    python mover_cache_db.py --dry      # só reporta (sem mover/remover)
"""
from __future__ import annotations

import argparse
import shutil
import sqlite3
from datetime import datetime
from pathlib import Path

from catalog_server.config import CACHE_DB, SYSTEM_DB
from catalog_server.db import CACHE_SCHEMA, init_cache_db

COLS = "url, site, html, bytes, url_final, produto_id, variante_id, origem, criada_em, atualizada_em"
COL_LIST = [c.strip() for c in COLS.split(",")]
BATCH = 250


def _table_exists(conn: sqlite3.Connection, name: str) -> bool:
    return conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)
    ).fetchone() is not None


def run(dry: bool) -> None:
    with sqlite3.connect(SYSTEM_DB, timeout=60) as src:
        src.row_factory = sqlite3.Row
        if not _table_exists(src, "paginas_fonte"):
            print("server.db não tem mais paginas_fonte. Nada a fazer.")
            return
        total = src.execute("SELECT COUNT(*) FROM paginas_fonte").fetchone()[0]
        print(f"linhas em server.db.paginas_fonte: {total}")

        if dry:
            print("DRY-RUN: nenhuma alteração feita.")
            return

        # backup do banco de cache (se já existir algo)
        if CACHE_DB.exists():
            dest = CACHE_DB.with_name(f"server_cache_backup_{datetime.now():%Y%m%d_%H%M%S}.db")
            shutil.copy2(CACHE_DB, dest)
            print(f"backup do cache antigo: {dest}")

        init_cache_db()
        with sqlite3.connect(CACHE_DB, timeout=60) as dst:
            moved = 0
            cur = src.execute(f"SELECT {COLS} FROM paginas_fonte")
            while True:
                rows = cur.fetchmany(BATCH)
                if not rows:
                    break
                cx = dst.cursor()
                cx.executemany(
                    f"INSERT OR IGNORE INTO paginas_fonte ({COLS}) VALUES"
                    f" ({','.join('?' * len(COL_LIST))})",
                    [tuple(r[k] for k in COL_LIST) for r in rows],
                )
                moved += cx.rowcount
                if moved % 5000 < BATCH:
                    dst.commit()
            dst.commit()
            dst.execute("PRAGMA optimize")
            print(f"copiadas para {CACHE_DB.name}: {moved}")

        # remove a tabela do banco principal
        for idx in ("idx_paginas_fonte_site", "idx_paginas_fonte_produto", "idx_paginas_fonte_variante"):
            src.execute(f"DROP INDEX IF EXISTS {idx}")
        src.execute("DROP TABLE IF EXISTS paginas_fonte")
        src.commit()
        print("tabela paginas_fonte removida do server.db")

    # recupera espaço em disco do banco principal
    w = sqlite3.connect(SYSTEM_DB, timeout=60)
    try:
        print("VACUUM (pode levar alguns minutos)...")
        w.execute("VACUUM")
        print("VACUUM concluído.")
    finally:
        w.close()

    size = SYSTEM_DB.stat().st_size / (1024 ** 2)
    print(f"server.db agora tem {size:.1f} MB")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry", action="store_true", help="não altera nada")
    args = ap.parse_args()
    run(dry=args.dry)


if __name__ == "__main__":
    main()