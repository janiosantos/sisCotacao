import re


PRICE_RE = re.compile(r"R\$\s*([0-9]+(?:\.[0-9]{3})*(?:,[0-9]{1,2})?)", re.I)

NON_DIGIT = re.compile(r"[^\d,]")


def parse_price_brl(text: str) -> float | None:

    if not text:
        return None

    match = PRICE_RE.search(text)

    if not match:
        match = PRICE_RE.search(text.replace("R$", "R$ "))
        if not match:
            return None

    raw = match.group(1)

    if "." in raw and "," in raw:

        raw = raw.replace(".", "").replace(",", ".")

    elif "," in raw:

        raw = raw.replace(",", ".")

    try:
        return float(raw)
    except ValueError:
        return None


def clean_text(text: str) -> str:

    if not text:
        return ""

    return " ".join(text.split())
