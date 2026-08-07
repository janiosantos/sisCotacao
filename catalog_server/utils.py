from __future__ import annotations

from pathlib import Path

from catalog_server.config import IMAGES_DIR


def image_url(filename: str | None) -> str | None:
    """Converte o caminho absoluto da imagem para URL do servidor."""
    if not filename:
        return None
    try:
        relative = Path(filename).resolve().relative_to(IMAGES_DIR.resolve())
        return "/images/" + relative.as_posix()
    except ValueError:
        return None


def product_code(row) -> str:
    sku = row["sku"] if "sku" in row.keys() else None
    if sku:
        return str(sku)
    return f"#{row['id']}"
