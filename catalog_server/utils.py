from __future__ import annotations

from pathlib import Path

from catalog_server.config import IMAGES_DIR


def image_url(filename: str | None) -> str | None:
    if not filename:
        return None
    # Tenta extrair a parte relativa após "images/"
    for sep in ("/images/", "\\images\\", "/images\\", "\\images/"):
        idx = filename.find(sep)
        if idx >= 0:
            relative = filename[idx + len(sep):].replace("\\", "/")
            if relative:
                return "/images/" + relative
    # Fallback: tenta resolver como Path
    try:
        p = Path(filename)
        if p.is_absolute():
            relative = p.relative_to(IMAGES_DIR.resolve())
            return "/images/" + relative.as_posix()
        # Já é relativo
        return "/images/" + p.as_posix()
    except (ValueError, OSError):
        return None


def product_code(row) -> str:
    sku = row["sku"] if "sku" in row.keys() else None
    if sku:
        return str(sku)
    return f"#{row['id']}"
