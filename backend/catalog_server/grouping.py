"""Agrupamento de produtos por variações (atributos estruturados).

Os atributos de variação (cor, bitola, potência, temperatura, formato, etc.)
são extraídos dos nomes dos produtos pelo script de enriquecimento
(`catalog_server.enrich`) e persistidos em campos estruturados na tabela
`product_attributes` do banco do catálogo.

Este módulo tem duas responsabilidades:

1. Extratores (`extract_attributes`) usados pelo enriquecimento — parsing dos
   nomes acontece UMA vez, fora do caminho de requisição.
2. Agrupamento (`build_meta` + `group_products`) que lê apenas os atributos já
   estruturados e monta os cards do catálogo.

Cada família de produto (cabo, lâmpada, parafuso) declara quais atributos são
variações e como eles são exibidos no seletor do catálogo.
"""
from __future__ import annotations

import re

_CORES = [
    "amarelo",
    "azul",
    "branco",
    "cinza",
    "marrom",
    "preto",
    "verde",
    "vermelho",
    "multicor",
    "rosa",
    "transparente",
    "cinza claro",
]

# Cabos: bitola ("2X1,50mm²", "4mm", "10mm²") e cor.
_MM_RE = re.compile(
    r"\d+(?:[.,]\d+)?\s*x\s*\d+(?:[.,]\d+)?\s*mm\u00b2?|\d+(?:[.,]\d+)?\s*mm\u00b2?",
    re.I,
)
_COLOR_RE = re.compile(r"\b(" + "|".join(_CORES) + r")\b", re.I)

# Lâmpadas / luminárias.
_POWER_RE = re.compile(r"\b(\d+(?:/\d+)?)\s*(?:w|watts)\b", re.I)
_TEMP_RE = re.compile(r"\b(\d{3,4})\s*k\b", re.I)
_SIZE_RE = re.compile(r"\b(\d{2,4}\s*[x×]\s*\d{2,4})\b", re.I)
_INSTALL_RE = re.compile(r"\b(embutir|sobrepor)\b", re.I)
_FORMAT_RE = re.compile(r"\b(quadrado|redondo|retangular)\b", re.I)
_BRANCO_TON_RE = re.compile(r"\bbranco\s+(quente|neutro|frio)\b", re.I)

# Parafusos.
_SCREW_SIZE_RE = re.compile(r"\b(\d+(?:[.,]\d+)?\s*[x×]\s*\d+(?:[.,]\d+)?\s*mm)\b", re.I)
_THREAD_RE = re.compile(
    r"\b(passo\s+fino|passo\s+grosso|rosca\s+fina|rosca\s+grossa|meia\s+rosca"
    r"|rosca\s+inteira|rosca\s+soberba|1/\d+|3/\d+|1/\d+|5/\d+)\b",
    re.I,
)
_HEAD_RE = re.compile(
    r"\b(sextavada|chata|escareada|panela|redonda|abaulada|cilíndrica|cilindrica"
    r"|lentilha|flangeada)\b",
    re.I,
)
_SLOT_RE = re.compile(
    r"\b(fenda\s+simples|fenda\s+reta|fenda\s+plana|phillips|estrela|cruz|allen"
    r"|sextavado\s+interno|torx)\b",
    re.I,
)
_TIP_RE = re.compile(r"\b(broca|agulha|auto[-\s]?atarraxante|plana|reta)\b", re.I)
_MATERIAL_RE = re.compile(
    r"\b(a[çc]o\s+inox|inox|zincado|bicromatizado|dourado|plástico|plastico|nylon|poliamida)\b",
    re.I,
)

_BRANDS = ["cobrecom", "corfio", "santa luiza", "match solutions", "sil", "taschibra"]
_NAME_BRAND_RE = re.compile(r"\b(cobrecom|corfio|sil|taschibra)\b", re.I)
_PLACEHOLDER_BRANDS = {"outras marcas", "marca padrao.", "marca padrão."}
_STOPWORDS = {"de", "do", "da", "dos", "das", "com", "em", "para", "e", "o", "a"}

PACKAGE_LABELS = {"rolo": "Rolo", "metro": "Avulso", "bobina": "Bobina"}

# (id, rótulo) dos atributos de variação de cada família.
FAMILY_ATTRS: dict[str, list[tuple[str, str]]] = {
    "cabo": [("color", "Cor"), ("diameter", "Bitola / Tamanho")],
    "lampada": [
        ("power", "Potência"),
        ("temperature", "Temperatura de Cor"),
        ("install", "Tipo de Instalação"),
        ("format", "Formato"),
        ("size", "Tamanho"),
    ],
    "parafuso": [
        ("diameter", "Diâmetro"),
        ("thread", "Tipo de Rosca"),
        ("head", "Tipo de Cabeça"),
        ("slot", "Tipo de Fenda"),
        ("tip", "Tipo de Ponta"),
        ("material", "Material / Tratamento"),
    ],
}

# Atributos de metadados guardados junto com os de variação (não são chips).
_META_ATTRS = {"family", "base", "package", "brand"}


def display_name(base: str) -> str:
    """Normaliza o case do nome base preservando tokens como PP, RG59, 750V."""
    out = []
    for w in base.split():
        if re.search(r"\d", w) or w.isupper():
            out.append(w)
        else:
            out.append(w.capitalize())
    return " ".join(out)


def extract_brand(product: dict) -> str | None:
    """Marca real: vem do nome (ex.: '... - Cobrecom - Rolo 100m')."""
    name = product.get("name") or ""
    m = _NAME_BRAND_RE.search(name)
    if m:
        b = m.group(1)
        return "SIL" if b.lower() == "sil" else b.capitalize()
    col = (product.get("brand") or "").strip()
    if col and col.lower() not in _PLACEHOLDER_BRANDS:
        return col
    return None


def detect_family(product: dict) -> str | None:
    """Identifica a família de produto (cabo, lampada, parafuso) ou None."""
    category = (product.get("category") or "").lower()
    sub = (product.get("subcategory") or "").lower()
    name = (product.get("name") or "").lower()
    blob = f"{category} {sub} {name}"
    if re.search(r"\b(cabo|fio)\b", blob) or "cftv" in blob or "multiplexado" in blob:
        return "cabo"
    if re.search(r"\b(lampada|luminaria|refletor|spot|pendente)\b", blob) or "ilumin" in blob:
        return "lampada"
    if re.search(r"\b(parafuso|porca|bucha|arruela)\b", blob):
        return "parafuso"
    return None


def _clean_base(name: str, patterns: list[re.Pattern]) -> str:
    base = name
    for pat in patterns:
        base = pat.sub(" ", base)
    for b in _BRANDS:
        base = re.sub(r"\b" + re.escape(b) + r"\b", " ", base, flags=re.I)
    base = re.sub(r"[-\u2013]+", " ", base)
    words = [w for w in base.split() if w.lower() not in _STOPWORDS and w not in {"*", "/", "&"}]
    return re.sub(r"\s+", " ", " ".join(words)).strip(" -")


def _cap_word(value: str) -> str:
    return " ".join(w.capitalize() for w in value.split())


# ---------------------------------------------------------------------------
# Extratores por família (usados pelo enriquecimento)
# ---------------------------------------------------------------------------

def _cable_attrs(product: dict) -> tuple[dict, str | None]:
    name = product.get("name") or ""
    lower = name.lower()
    attrs: dict = {}
    mm = re.findall(_MM_RE, name)
    if mm:
        attrs["diameter"] = mm[0].strip()
    cm = re.search(_COLOR_RE, lower)
    if cm:
        attrs["color"] = cm.group(1)
    if "rolo" in lower:
        package = "rolo"
    elif "bobina" in lower:
        package = "bobina"
    elif "metro" in lower or re.search(r"\bm\b", lower):
        package = "metro"
    else:
        package = None
    return attrs, package


_CABLE_PATTERNS = [
    _MM_RE,
    _COLOR_RE,
    re.compile(r"\b(?:rolo|bobina)\s+\d+\s*m(?:etros)?\b", re.I),
    re.compile(r"\b(rolo|bobina|metro)\b", re.I),
]


def _lamp_attrs(product: dict) -> dict:
    name = product.get("name") or ""
    lower = name.lower()
    attrs: dict = {}
    pw = re.search(_POWER_RE, lower)
    if pw:
        attrs["power"] = pw.group(1).upper() + "W"
    tp = re.search(_TEMP_RE, lower)
    if tp:
        attrs["temperature"] = tp.group(1) + "K"
    sz = re.search(_SIZE_RE, name)
    if sz:
        attrs["size"] = sz.group(1).replace(" ", "").replace("×", "x").upper()
    ins = re.search(_INSTALL_RE, lower)
    if ins:
        attrs["install"] = ins.group(1).capitalize()
    fm = re.search(_FORMAT_RE, lower)
    if fm:
        attrs["format"] = fm.group(1).capitalize()
    elif sz:
        a, b = re.findall(r"\d+", sz.group(1))
        attrs["format"] = "Quadrado" if a == b else "Retangular"
    return attrs


_LAMP_PATTERNS = [_POWER_RE, _TEMP_RE, _SIZE_RE, _INSTALL_RE, _FORMAT_RE, _BRANCO_TON_RE]


def _screw_attrs(product: dict) -> dict:
    name = product.get("name") or ""
    lower = name.lower()
    attrs: dict = {}
    ss = re.search(_SCREW_SIZE_RE, lower)
    if ss:
        attrs["diameter"] = ss.group(1).replace(" ", "")
    for attr_id, regex in (
        ("thread", _THREAD_RE),
        ("head", _HEAD_RE),
        ("slot", _SLOT_RE),
        ("tip", _TIP_RE),
        ("material", _MATERIAL_RE),
    ):
        m = regex.search(lower)
        if m:
            attrs[attr_id] = _cap_word(re.sub(r"\s+", " ", m.group(1)).strip())
    return attrs


_SCREW_PATTERNS = [_SCREW_SIZE_RE, _THREAD_RE, _HEAD_RE, _SLOT_RE, _TIP_RE, _MATERIAL_RE]


def extract_attributes(product: dict) -> dict:
    """Extrai todos os atributos estruturados de um produto (para enriquecimento)."""
    family = detect_family(product)
    attrs: dict = {"family": family}
    if not family:
        return attrs
    name = product.get("name") or ""
    if family == "cabo":
        a, package = _cable_attrs(product)
        attrs.update(a)
        attrs["package"] = package
        base = _clean_base(name, _CABLE_PATTERNS)
    elif family == "lampada":
        attrs.update(_lamp_attrs(product))
        base = _clean_base(name, _LAMP_PATTERNS)
    else:
        attrs.update(_screw_attrs(product))
        base = _clean_base(name, _SCREW_PATTERNS)
    brand = extract_brand(product)
    if brand:
        attrs["brand"] = brand
    if base:
        attrs["base"] = base
    return attrs


# ---------------------------------------------------------------------------
# Agrupamento (lê apenas atributos estruturados)
# ---------------------------------------------------------------------------

def build_meta(product_view: dict, attrs: dict) -> dict:
    """Monta o '_meta' de agrupamento a partir dos atributos vindos do banco."""
    base = attrs.get("base") or (product_view.get("name") or "")
    package = attrs.get("package")
    return {
        "key": (base, package),
        "family": attrs.get("family"),
        "base": base,
        "package": package,
        "attrs": {k: v for k, v in attrs.items() if k not in _META_ATTRS},
        "brand": attrs.get("brand"),
    }


def _option_sort_key(val: str):
    m = re.match(r"([\d.,]+)", val.replace(",", "."))
    if m:
        try:
            return (0, float(m.group(1)))
        except ValueError:
            pass
    return (1, val.lower())


def _variant_view(v: dict) -> dict:
    meta = v["_meta"]
    return {
        "id": v["id"],
        "sku": v["sku"],
        "name": v["name"],
        "brand": meta["brand"],
        "attrs": meta["attrs"],
        "price": v["price"],
        "imagem_url": v["imagem_url"],
    }


def _single_view(v: dict) -> dict:
    meta = v["_meta"]
    return {
        "group": False,
        "id": v["id"],
        "sku": v["sku"],
        "ean": v["ean"],
        "name": v["name"],
        "base": meta["base"],
        "package": meta["package"],
        "package_label": PACKAGE_LABELS.get(meta["package"], ""),
        "attrs": meta["attrs"],
        "brand": v["brand"],
        "price": v["price"],
        "old_price": v["old_price"],
        "pix_price": v["pix_price"],
        "installment": v["installment"],
        "category": v["category"],
        "subcategory": v["subcategory"],
        "imagem_url": v["imagem_url"],
    }


def _group_view(rep: dict, variants: list[dict], base: str, package: str | None) -> dict:
    prices = [v["price"] or 0 for v in variants]
    family = rep["_meta"]["family"]
    schema = FAMILY_ATTRS.get(family, [])
    attr_defs = []
    for attr_id, label in schema:
        opts = sorted(
            {v["_meta"]["attrs"].get(attr_id) for v in variants if v["_meta"]["attrs"].get(attr_id)},
            key=_option_sort_key,
        )
        if len(opts) >= 2:
            attr_defs.append({"id": attr_id, "label": label, "options": opts})
    brands = sorted({v["_meta"]["brand"] for v in variants if v["_meta"]["brand"]})
    return {
        "group": True,
        "id": rep["id"],
        "sku": rep["sku"],
        "name": base,
        "base": base,
        "package": package,
        "package_label": PACKAGE_LABELS.get(package, ""),
        "price_min": min(prices),
        "price_max": max(prices),
        "brand": rep["_meta"]["brand"],
        "category": rep["category"],
        "subcategory": rep["subcategory"],
        "imagem_url": rep["imagem_url"],
        "attrs": attr_defs,
        "brands": brands,
        "variants": [_variant_view(v) for v in variants],
        "variant_count": len(variants),
    }


def group_products(product_views: list[dict]) -> list[dict]:
    """Recebe as linhas de produto (com '_meta') e retorna os cards do catálogo."""
    best: dict[tuple, dict] = {}
    for pv in product_views:
        m = pv["_meta"]
        subkey = (
            m["key"][0],
            m["key"][1],
            m["family"],
            m["brand"],
            frozenset(m["attrs"].items()),
        )
        cur = best.get(subkey)
        if cur is None or (pv["price"] or 0) < (cur["price"] or 0) or (
            (pv["price"] or 0) == (cur["price"] or 0) and pv["id"] < cur["id"]
        ):
            best[subkey] = pv

    groups: dict[tuple, list[dict]] = {}
    for pv in best.values():
        groups.setdefault(pv["_meta"]["key"], []).append(pv)

    cards: list[dict] = []
    for (base, package), variants in groups.items():
        family = variants[0]["_meta"]["family"]
        schema = FAMILY_ATTRS.get(family, [])
        variants.sort(
            key=lambda v: (
                tuple(v["_meta"]["attrs"].get(attr_id) or "" for attr_id, _ in schema),
                v["_meta"]["brand"] or "",
            )
        )
        if len(variants) > 1:
            rep = min(variants, key=lambda v: (v["price"] or 0, v["id"]))
            cards.append(_group_view(rep, variants, display_name(rep["_meta"]["base"]), package))
        else:
            cards.append(_single_view(variants[0]))

    cards.sort(key=lambda c: (c["name"] or "").lower())
    return cards
