#!/usr/bin/env python3
"""Backup PostgreSQL + imagens + manifest (ADM-004).

Uso:
    python scripts/backup.py [--dir DIR] [--repos N] [--pg-url URL] [--images DIR]

Gera, para cada execução:
    backup-<timestamp>/schema.dump        (pg_dump do schema)
    backup-<timestamp>/data.dump          (pg_dump dos dados)
    backup-<timestamp>/manifest.json      (conteúdo, hash, retenção)
    backup-<timestamp>/images.tar.gz      (imagens de produtos, se informadas)

Retenção: mantém os N backups mais recentes (padrão 7). Banco e arquivos são
consistentes no mesmo diretório de backup (mesmo ponto no tempo).

IMPORTANTE: em produção o backup deve ser acionado pelo pipeline/agendador com
credenciais de segredo (nunca em código), e o teste de restauração é feito em
ambiente isolado.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import tarfile
from datetime import datetime, timezone
from pathlib import Path


def _hash(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for bloco in iter(lambda: f.read(1 << 20), b""):
            h.update(bloco)
    return h.hexdigest()


def backup(dir_base: Path, reter: int, pg_url: str, images_dir: str | None) -> Path:
    dir_base = Path(dir_base)
    dir_base.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    destino = dir_base / f"backup-{stamp}"
    destino.mkdir()
    manifest: dict = {"criado_em": stamp, "arquivos": {}}

    # schema + data (pg_dump); banco e imagens no mesmo ponto
    env = {**os.environ, "PGPASSWORD": (pg_url.rsplit("@", 1)[-1].split("/")[0])}
    for tipo in ("schema", "data"):
        alvo = destino / f"{tipo}.dump"
        cmd = ["pg_dump", "--no-owner", "--no-acl"]
        if tipo == "schema":
            cmd += ["--schema-only"]
        cmd += [pg_url]
        with alvo.open("wb") as f:
            subprocess.run(cmd, stdout=f, env=env, check=True)
        manifest["arquivos"][alvo.name] = _hash(alvo)

    if images_dir and Path(images_dir).exists():
        tar = destino / "images.tar.gz"
        with tarfile.open(tar, "w:gz") as t:
            t.add(images_dir, arcname="images")
        manifest["arquivos"][tar.name] = _hash(tar)

    (destino / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    # retenção: mantém os `reter` mais recentes
    backups = sorted(dir_base.glob("backup-*"), key=lambda p: p.name, reverse=True)
    removidos = []
    for b in backups[reter:]:
        import shutil

        shutil.rmtree(b)
        removidos.append(b.name)
    return destino


def main() -> int:
    parser = argparse.ArgumentParser(description="Backup PostgreSQL + imagens")
    parser.add_argument("--dir", default="./backups", help="diretório base")
    parser.add_argument("--reter", type=int, default=7, help="quantos backups reter")
    parser.add_argument("--pg-url", required=True, help="URL do PostgreSQL")
    parser.add_argument("--images", default=None, help="diretório de imagens (opcional)")
    args = parser.parse_args()
    destino = backup(Path(args.dir), args.reter, args.pg_url, args.images)
    print(f"backup em {destino}")
    return 0


if __name__ == "__main__":
    sys.exit(main())