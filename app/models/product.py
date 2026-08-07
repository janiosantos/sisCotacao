from dataclasses import dataclass, field


@dataclass(slots=True)
class Product:

    id: int | None = None

    category_id: int | None = None

    url: str = ""

    sku: str = ""

    ean: str = ""

    name: str = ""

    brand: str = ""

    color: str = ""

    price: float = 0.0

    old_price: float | None = None

    pix_price: float = 0.0

    installment: str = ""

    short_description: str = ""

    long_description: str = ""

    category: str = ""

    subcategory: str = ""

    images: list[str] = field(default_factory=list)

    image_files: list[str] = field(default_factory=list)
