"""Classificação do catálogo: categoria / subcategoria a partir de breadcrumb da loja.

- A fonte mais fiel é o breadcrumb que cada loja expõe na página de produto:
  * Anhanguera Ferramentas   -> HTML `div.breadcrumb a`
  * Casa dos Parafusos        -> HTML `[itemtype*="BreadcrumbList"]`
  * Casa do Eletricista       -> JSON-LD `BreadcrumbList`
- Caso a loja não exponha breadcrumb (ex.: Casa Mattos) ou a extração falhe,
  usa-se o fallback por palavras-chave no nome do produto.
"""
from __future__ import annotations

import re
import unicodedata

from app.services.html_service import HtmlService
from app.utils.jsonld_utils import jsonld_by_type, jsonld_entries

# Termos de cabeçalho de breadcrumb a remover (não são categorias).
_BC_HEAD = {"home", "início", "inicio", "página inicial", "pagina inicial", "/"}

# Ruído comum dentro de contêineres de breadcrumb (não são etapas de categoria).
_BC_NOISE = (
    "produto fora de linha",
    "produtos relacionados",
    "relacionados",
    "ofertas",
    "desconto",
    "% off",
    "ver todos",
    "categoria",
)

# Palavras-chave nome -> caminho de subcategoria (fallback p/ lojas sem breadcrumb).
_KEYWORDS: list[tuple[re.Pattern, str]] = [
    (re.compile(r"parafuso|parafusadeira|broca|bucha|chumbador", re.I), "Fixadores > Parafusos"),
    (re.compile(r"esmerilhadeira|martelete|furadeira|parafusadeira|serra|tupia|retifica|soprador|flex|maquina|cortador|jiqushita|broca|disco de corte", re.I), "Ferramentas"),
    (re.compile(r"cabo flex|fio|cabinho|hepr|flex sil", re.I), "Fios e Cabos > Cabo Flexível"),
    (re.compile(r"l[âa]mpada|led|lumin[âa]ria|refletor|b[jj]u|spot", re.I), "Iluminação"),
    (re.compile(r"chuveiro|chuveiro el[ée]trico|ducha|torneira|registro", re.I), "Hidráulica"),
    (re.compile(r"materia|disjuntor|interruptor|tomada|quadro|dps|conector|terminal", re.I), "Material Elétrico"),
    (re.compile(r"abitacão|aulas|metro|paqu[íi]metro|n[íi]vel a laser|medidor", re.I), "Medição"),
    (re.compile(r"c[âa]mera|ssalm|alarme|fusível|tipo", re.I), "Segurança e Vigilância"),
    (re.compile(r"broca|verador|jogo de|ate|suíte|bed entrega", re.I), "Acessórios"),
]


def extract_breadcrumb(html: str | None, url: str = "", product_name: str = "") -> list[str]:
    """Devolve a sequência de categorias do breadcrumb (sem cabeçalho/produto)."""
    if not html:
        return []
    from urllib.parse import urlparse

    host = (urlparse(url).hostname or "").lower()
    soup = HtmlService.soup(html)
    items: list[str] = []

    if "anhanguera" in host:
        node = soup.select_one(".breadcrumb")
        if node is not None:
            items = [t.strip() for t in node.stripped_strings]
    elif "casadosparafusos" in host:
        node = soup.select_one('[itemtype*="BreadcrumbList"]')
        if node is not None:
            items = [t.strip() for t in node.stripped_strings]
    elif "casadoeletricistascas" in host:
        items = _jsonld_breadcrumb(soup)

    if not items:
        items = _jsonld_breadcrumb(soup)

    items = _clean(items, product_name)

    # Na Casa dos Parafusos a última etapa do BreadcrumbList é sempre o produto
    # em si (não é categoria); se o match por nome não removeu, remove aqui.
    if "casadosparafusos" in host and len(items) > 1:
        items = items[:-1]

    return items


def _jsonld_breadcrumb(soup) -> list[str]:
    for entry in jsonld_entries(soup):
        if entry.get("@type") == "BreadcrumbList":
            elems = entry.get("itemListElement") or []
            return [str(i.get("name") or "").strip() for i in elems]
    return []


def _norm(text: str) -> str:
    text = unicodedata.normalize("NFKD", text or "").encode("ascii", "ignore").decode()
    return re.sub(r"\s+", " ", text).strip().lower()


def _clean(items: list[str], product_name: str) -> list[str]:
    pn = _norm(product_name)
    pn = pn.rstrip(".").rstrip()
    out: list[str] = []
    for raw in items:
        t = re.sub(r"\s+", " ", (raw or "")).strip()
        if not t:
            continue
        nt = _norm(t).rstrip(".").rstrip()
        if nt in _BC_HEAD:
            continue
        if any(k and k in nt for k in _BC_NOISE):
            continue
        out.append(t)
    # Última etapa do breadcrumb costuma ser o nome do produto (ex.: Casa dos
    # Parafusos) — remove se corresponder ao nome (completo ou prefixo truncado).
    while out:
        last = _norm(out[-1]).rstrip(".").rstrip()
        if pn and (last == pn or (len(last) > 3 and pn.startswith(last))):
            out.pop()
        else:
            break
    return out


def categoria(items: list[str]) -> str:
    """Categoria = nível raiz do breadcrumb (primeiro elemento)."""
    return items[0] if items else ""


def categoria_path(items: list[str]) -> str:
    """Caminho completo para exibição (join raiz > subcategoria)."""
    return " > ".join(items)


def subcategoria(items: list[str]) -> str:
    """Subcategoria = folha do breadcrumb (último elemento)."""
    return items[-1] if items else ""


def fallback_categoria(name: str, marca: str = "") -> list[str]:
    """Fallback (sem breadcrumb) por palavras-chave no nome/marca do produto."""
    alvo = f"{marca} {name}".lower()
    for pattern, path in _KEYWORDS:
        if pattern.search(alvo):
            return [p.strip() for p in path.split(">")]
    return []