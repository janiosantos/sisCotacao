import json

from bs4 import BeautifulSoup

from app.selectors.product_selectors import JSONLD_SCRIPT


def jsonld_entries(soup: BeautifulSoup) -> list[dict]:

    entries = []

    for script in soup.select(JSONLD_SCRIPT):

        if not script.string:
            continue

        try:
            data = json.loads(script.string)
        except (json.JSONDecodeError, ValueError):
            continue

        if isinstance(data, list):
            entries.extend(data)
        elif isinstance(data, dict):
            entries.append(data)

    return entries


def jsonld_by_type(entries: list[dict], object_type: str) -> dict | None:

    for entry in entries:

        if entry.get("@type") == object_type:
            return entry

    return None
