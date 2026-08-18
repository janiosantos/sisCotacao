"""Backup manual do banco de dados (antes de migrações/incidentes).

Copia os bancos SQLite do sistema para uma pasta timestampada em
`Backups/manual/`. Usa a API de backup do sqlite3 (cópia consistente, mesmo
com WAL). Não é um `DROP`/destrutivo — apenas leitura e cópia.

Uso:
    python scripts/backup_db.py [--dest DIR] [--incluir-cache]

O cache de páginas (server_cache.db) pode ter muitos GB e é lento de copiar;
por padrão é ignorado — use `--incluir-cache` quando precisar dele.
"""
from __future__ import annotations

import argparse
import shutil
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from catalog_server.config import CACHE_DB, CATALOG_DB, MODULE_DIR, SYSTEM_DB

DEFAULT_DEST = MODULE_DIR.parent / "Backups" / "manual"


def backup_sqlite(src: Path, dest: Path) -> Path:
    """Copia `src` (arquivo SQLite) para `dest` usando a API de backup."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    src_conn = sqlite3.connect(f"file:{src.resolve().as_posix()}?mode=ro", uri=True)
    dst_conn = sqlite3.connect(dest)
    try:
        src_conn.backup(dst_conn)
    finally:
        dst_conn.close()
        src_conn.close()
    return dest


def main() -> int:
    ap = argparse.ArgumentParser(description="Backup manual dos bancos SQLite")
    ap.add_argument("--dest", type=Path, default=DEFAULT_DEST)
    ap.add_argument(
        "--incluir-cache",
        action="store_true",
        help="inclui o server_cache.db (pode ter vários GB e ser lento)",
    )
    args = ap.parse_args()

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    dest_dir = args.dest / stamp
    dest_dir.mkdir(parents=True, exist_ok=True)

    sources: list[tuple[Path, str]] = [
        (SYSTEM_DB, "server.db"),
        (CATALOG_DB, "crawler.db"),
    ]
    if args.incluir_cache:
        sources.append((CACHE_DB, "server_cache.db"))

    done: list[Path] = []
    for src, label in sources:
        if not src.exists():
            print(f"ignorado (não existe): {src}")
            continue
        try:
            out = backup_sqlite(src, dest_dir / label)
            size_mb = round(out.stat().st_size / (1024 * 1024), 2)
            done.append(out)
            print(f"backup ok: {out} ({size_mb} MB)")
        except Exception as exc:  # pragma: no cover - erro de I/O raro
            print(f"ERRO no backup de {src}: {exc}")
            return 1

    if not done:
        print("nenhum banco encontrado para backup.")
        return 1

    print(f"\nBackup completo em: {dest_dir}")
    print("Para restaurar: pare o servidor e copie os arquivos de volta para:")
    print(f"  {SYSTEM_DB.parent}")
    return 0


if __name__ == "__main__":
    sys.exit(main())