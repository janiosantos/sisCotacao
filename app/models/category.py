from dataclasses import dataclass


@dataclass(slots=True)
class Category:

    id: int | None = None

    parent_id: int | None = None

    level: int = 0

    name: str = ""

    slug: str = ""

    breadcrumb: str = ""

    url: str = ""