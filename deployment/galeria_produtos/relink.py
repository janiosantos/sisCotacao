"""Substitui copias da galeria por hardlinks usando um unico bind mount."""
from __future__ import annotations

import argparse
import json
import os
import sqlite3
from contextlib import closing
from pathlib import Path


def _safe_path(root: Path, relative: str) -> Path:
    path = (root / relative).resolve()
    try:
        path.relative_to(root)
    except ValueError as exc:
        raise RuntimeError(f"Caminho fora da raiz permitida: {relative}") from exc
    return path


def relink(images_dir: Path, gallery_dir: Path) -> dict[str, int | bool]:
    images_root = images_dir.resolve()
    media_root = (gallery_dir / "media").resolve()
    database = gallery_dir / "gallery.sqlite3"
    if not database.is_file() or not media_root.is_dir():
        raise RuntimeError("Galeria exportada nao encontrada")
    if images_root.stat().st_dev != media_root.stat().st_dev:
        raise RuntimeError("Origem e galeria continuam em filesystems diferentes")

    linked = 0
    already_linked = 0
    freed_bytes_estimate = 0
    with closing(sqlite3.connect(database)) as conn:
        rows = conn.execute(
            "SELECT id,source_path,relative_path,bytes FROM images ORDER BY id"
        )
        for image_id, source_relative, target_relative, expected_bytes in rows:
            source = _safe_path(images_root, source_relative)
            target = _safe_path(media_root, target_relative)
            if not source.is_file() or not target.is_file():
                raise RuntimeError(f"Imagem {image_id} ausente na origem ou na galeria")
            source_stat = source.stat()
            target_stat = target.stat()
            if source_stat.st_size != expected_bytes or target_stat.st_size != expected_bytes:
                raise RuntimeError(f"Imagem {image_id} possui tamanho divergente")
            if os.path.samestat(source_stat, target_stat):
                already_linked += 1
                continue

            temporary = target.with_name(f".{target.name}.relink-{os.getpid()}")
            try:
                temporary.unlink(missing_ok=True)
                os.link(source, temporary)
                os.replace(temporary, target)
            finally:
                temporary.unlink(missing_ok=True)
            linked += 1
            freed_bytes_estimate += int(expected_bytes)
            if linked % 5000 == 0:
                print(f"deduplicate-images: {linked}", flush=True)

    return {
        "same_filesystem": True,
        "linked": linked,
        "already_linked": already_linked,
        "total": linked + already_linked,
        "freed_bytes_estimate": freed_bytes_estimate,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--images-dir", required=True)
    parser.add_argument("--gallery-dir", required=True)
    args = parser.parse_args()
    result = relink(Path(args.images_dir), Path(args.gallery_dir))
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
