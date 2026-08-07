from __future__ import annotations

import csv
from pathlib import Path

from app.config.settings import OUTPUT_FOLDER
from app.repositories.product_repository import ProductRepository

COLUMNS = [
    "URL",
    "SKU",
    "EAN",
    "Nome",
    "Categoria",
    "Subcategoria",
    "Marca",
    "Cor",
    "Preço",
    "Preço Antigo",
    "Preço Pix",
    "Parcelamento",
    "Descrição Curta",
    "Descrição Longa",
    "Imagens (URLs)",
    "Imagens (Arquivos)",
]


class CsvExporter:

    def __init__(self, repo: ProductRepository):

        self.repo = repo

    # ----------------------------------------------------------

    def export(self, path: Path | None = None) -> Path:

        path = path or OUTPUT_FOLDER / "products.csv"

        path.parent.mkdir(parents=True, exist_ok=True)

        rows = self.repo.export_rows()

        with open(
            path,
            "w",
            newline="",
            encoding="utf-8-sig",
        ) as fp:

            writer = csv.writer(fp)

            writer.writerow(COLUMNS)

            for row in rows:

                writer.writerow(
                    [
                        row.get("url") or "",
                        row.get("sku") or "",
                        row.get("ean") or "",
                        row.get("name") or "",
                        row.get("category") or "",
                        row.get("subcategory") or "",
                        row.get("brand") or "",
                        row.get("color") or "",
                        self._money(row.get("price")),
                        self._money(row.get("old_price")),
                        self._money(row.get("pix_price")),
                        row.get("installment") or "",
                        row.get("short_description") or "",
                        row.get("long_description") or "",
                        row.get("image_urls") or "",
                        row.get("image_files") or "",
                    ]
                )

        return path

    # ----------------------------------------------------------

    @staticmethod
    def _money(value) -> str:

        if value is None:
            return ""

        try:
            return f"{float(value):.2f}"
        except (TypeError, ValueError):
            return ""
