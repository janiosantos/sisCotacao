"""Importação de produto a partir de uma URL.

Reutiliza o parser do scraper (`app.parsers.product_parser`) para extrair os
dados do produto (nome, sku, marca, preços, fotos) e o enriquecimento
(`catalog_server.grouping.extract_attributes`) para identificar a família e os
atributos de variação. Com apenas a URL informada, o serviço é capaz de:

- garantir/ criar a família (create-or-get) com os atributos de variação;
- criar o `produtos_cadastro` (pai) com nome base, marca e descrição;
- criar uma `variante` com sku/ean/preços e seus `variante_atributos`;
- baixar as fotos do produto (mantendo as de alta resolução e descartando
  miniaturas/banners).

O fluxo é dividido em duas etapas:

1. `parse_url(url)` — só lê a página e devolve um "preview" dos dados
   (usado para o usuário conferir antes de confirmar).
2. `criar_produto_por_url(url)` — reparseia e cria tudo, devolvendo o id.

O serviço sempre baixa a página da loja (não há cache de páginas-fonte).
"""
from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import quote, urljoin, urlparse

import requests

from catalog_server.services.safe_http import get_public

from app.parsers.product_parser import ProductParser
from app.parsers.product_parser_anhangueraferramentas import ProductParserAnhangueraFerramentas
from app.parsers.product_parser_casadosparafusos import ProductParserCasadosParafusos
from app.parsers.product_parser_casamattos import ProductParserCasaMattos
from catalog_server import categorias
from catalog_server import classification
from catalog_server.db import system_conn
from catalog_server.grouping import (
    FAMILY_ATTRS,
    _META_ATTRS,
    display_name,
    extract_attributes,
    extract_brand,
)
from catalog_server.services import imagens_service
from catalog_server.services.sku_service import reservar as reservar_sku

_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/138.0 Safari/537.36"
)

_HEADERS = {"User-Agent": _UA, "Accept-Language": "pt-BR,pt;q=0.9"}

# Nomes das famílias no cadastro (mesmos usados pela sincronização do scraper).
FAMILY_DISPLAY = {
    "cabo": "Cabo Flexível",
    "lampada": "Lâmpada",
    "parafuso": "Parafuso",
}

DEFAULT_FAMILY = "Importados"


def _parser_for(url: str):
    """Devolve o parser adequado conforme o domínio do produto."""
    host = (urlparse(url).hostname or "").lower()
    if "casadosparafusos" in host:
        return ProductParserCasadosParafusos()
    if "casamattos" in host:
        return ProductParserCasaMattos()
    if "anhangueraferramentas" in host:
        return ProductParserAnhangueraFerramentas()
    return ProductParser()


class ParseError(Exception):
    """Falha ao interpretar a URL informada."""


def _quote_url(url: str) -> str:
    """Percent-encode de caracteres não-ASCII da URL.

    O `requests` codifica a URL como latin-1 internamente e falha em slugs com
    en dash (U+2013) ou aspas (U+2019) — comuns na Casa dos Parafusos. A URL
    original (sem encode) é mantida no banco para o dedup por URL.
    """
    return quote(url, safe=":/?#[]@!$&'()*+,;=%~-._")


def _fetch_html(url: str) -> tuple[str, str]:
    """Baixa a página e devolve (html, url_final)."""
    resp = get_public(_quote_url(url), timeout=40, headers=_HEADERS, max_bytes=5 * 1024 * 1024)
    resp.raise_for_status()
    if not resp.text or not resp.text.strip():
        raise ParseError("A página não retornou conteúdo.")
    return resp.text, resp.url


def parse_url(url: str) -> dict:
    """Baixa a página e extrai os dados estruturados do produto."""
    url = (url or "").strip()
    if not url:
        raise ParseError("Informe a URL do produto.")
    if not url.startswith(("http://", "https://")):
        raise ParseError("URL inválida: informe um endereço completo (https://...).")

    html, final_url = _fetch_html(url)
    data = _parser_for(url).parse(html, url=url)
    if not data.get("name"):
        raise ParseError(
            "Não foi possível identificar o produto na página. "
            "Verifique se a URL aponta para uma página de produto."
        )
    data["final_url"] = final_url
    data["attrs"] = extract_attributes(data)
    items = classification.extract_breadcrumb(html, url, data.get("name") or "")
    if not items:
        items = classification.fallback_categoria(
            data.get("name") or "", extract_brand(data) or ""
        )
    data["categoria"] = classification.categoria(items)
    data["subcategoria"] = classification.subcategoria(items)
    return data


def preview(data: dict) -> dict:
    """Monta o preview exibido ao usuário antes de confirmar o cadastro."""
    attrs = data.get("attrs") or {}
    family_key = attrs.get("family")
    labels = dict(FAMILY_ATTRS.get(family_key, []))
    return {
        "url": data.get("url") or "",
        "nome": data.get("name") or "",
        "sku": data.get("sku") or "",
        "ean": data.get("ean") or "",
        "marca": (
            extract_brand({"name": data.get("name") or "", "brand": data.get("brand") or ""})
            or ""
        ),
        "cor": data.get("color") or "",
        "preco": data.get("price"),
        "preco_de": data.get("old_price"),
        "preco_pix": data.get("pix_price"),
        "parcelamento": data.get("installment") or "",
        "fotos": len(data.get("images") or []),
        "family_key": family_key,
        "familia_nome": (
            FAMILY_DISPLAY.get(family_key) if family_key else DEFAULT_FAMILY
        ),
        "base": display_name(attrs.get("base") or data.get("name") or ""),
        "atributos": [
            {"label": labels.get(aid, aid), "valor": val}
            for aid, val in attrs.items()
            if aid not in _META_ATTRS and val
        ],
    }


def _ensure_familia(conn, nome: str, family_key: str, values_by_attr: dict) -> tuple[int, dict[str, int]]:
    """Garante a família (create-or-get) e seus atributos de variação."""
    row = conn.execute(
        "SELECT id FROM familias WHERE LOWER(nome)=LOWER(?)", (nome,)
    ).fetchone()
    if row:
        familia_id = row["id"]
    else:
        familia_id = conn.execute(
            "INSERT INTO familias (nome, descricao) VALUES (?,?)",
            (nome, f"Importada da URL (família {family_key})"),
        ).lastrowid

    existing = {
        r["nome"]: r["id"]
        for r in conn.execute(
            "SELECT id, nome FROM familia_atributos WHERE familia_id=?", (familia_id,)
        ).fetchall()
    }
    label_to_id: dict[str, int] = {}
    for attr_id, label in FAMILY_ATTRS.get(family_key, []):
        values = values_by_attr.get(attr_id, [])
        aid = existing.get(label)
        if aid:
            try:
                opts = json.loads(
                    conn.execute(
                        "SELECT opcoes FROM familia_atributos WHERE id=?", (aid,)
                    ).fetchone()["opcoes"] or "[]"
                )
            except (ValueError, TypeError):
                opts = []
            merged = list(dict.fromkeys(opts + values))
            conn.execute(
                "UPDATE familia_atributos SET opcoes=? WHERE id=?",
                (json.dumps(merged, ensure_ascii=False), aid),
            )
        else:
            aid = conn.execute(
                "INSERT INTO familia_atributos (familia_id, nome, tipo, opcoes, ordem)"
                " VALUES (?,?,?,?,?)",
                (familia_id, label, "lista", json.dumps(values, ensure_ascii=False), len(existing) + 1),
            ).lastrowid
        label_to_id[label] = aid
    return familia_id, label_to_id


def _to_float(value):
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _absolute_images(imagens: list[str], base_url: str) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for u in imagens or []:
        if not u or u.startswith("data:"):
            continue
        full = urljoin(base_url, u)
        if full in seen:
            continue
        seen.add(full)
        out.append(full)
    return out


def _baixar_imagem(produto_id: int, img_url: str, page_url: str) -> Path | None:
    """Baixa e valida a imagem, devolvendo o caminho salvo (ou None)."""
    try:
        r = get_public(
            _quote_url(img_url),
            timeout=30,
            headers={"User-Agent": _UA, "Referer": _quote_url(page_url)},
            max_bytes=10 * 1024 * 1024,
        )
        r.raise_for_status()
    except requests.RequestException:
        return None
    ctype = r.headers.get("Content-Type", "")
    if not (ctype.startswith("image/") or imagens_service._is_direct_image(img_url)):
        return None
    size = imagens_service._image_size(r.content)
    if size and max(size) < imagens_service._MIN_DIMENSION:
        return None
    try:
        return imagens_service._save_bytes(produto_id, img_url, r.content)
    except OSError:
        return None


def criar_produto_por_url(
    url: str,
    categoria: str = "",
    subcategoria: str = "",
) -> dict:
    """Cria família, produto, variação, atributos e fotos a partir de uma URL."""
    data = parse_url(url)
    attrs = data.get("attrs") or {}
    family_key = attrs.get("family")
    fname = FAMILY_DISPLAY.get(family_key) if family_key else DEFAULT_FAMILY
    base = display_name(attrs.get("base") or data.get("name") or "")
    marca = (
        extract_brand({"name": data.get("name") or "", "brand": data.get("brand") or ""})
        or ""
    )
    descricao = (data.get("short_description") or data.get("long_description") or "").strip()
    # Classificação automática por breadcrumb (ou fallback por nome) quando não
    # for informada explicitamente.
    if not (categoria or "").strip():
        categoria = data.get("categoria") or ""
    if not (subcategoria or "").strip():
        subcategoria = data.get("subcategoria") or ""

    variation_attrs = {
        aid: val for aid, val in attrs.items() if aid not in _META_ATTRS and val
    }
    values_by_attr = {aid: [val] for aid, val in variation_attrs.items()}

    url_final = data.get("url") or url
    preco = _to_float(data.get("price")) or 0
    pix = _to_float(data.get("pix_price"))
    old = _to_float(data.get("old_price"))

    with system_conn() as conn:
        familia_id, label_to_id = _ensure_familia(
            conn, fname, family_key or "", values_by_attr
        )
        categoria_id, subcategoria_id = categorias.resolve(conn, categoria, subcategoria)

        produto_id = conn.execute(
            "INSERT INTO produtos_cadastro (familia_id, nome, marca, descricao,"
            " categoria_id, subcategoria_id, embalagem, url)"
            " VALUES (?,?,?,?,?,?,?,?)",
            (familia_id, base, marca, descricao, categoria_id, subcategoria_id,
             attrs.get("package") or "", url_final),
        ).lastrowid

        vid = conn.execute(
            "INSERT INTO produtos_cadastro (sku, ean, preco, preco_promocional, old_price,"
            " pix_price, installment, url, marca, atributos)"
            " VALUES (?,?,?,?,?,?,?,?,?,?)",
            ("", data.get("ean") or "", preco, pix, old,
             pix, data.get("installment") or "", url_final, marca,
             json.dumps({}, ensure_ascii=False)),
        ).lastrowid

        labels = dict(FAMILY_ATTRS.get(family_key, []))
        attrs_json: dict[str, str] = {}
        for aid, val in variation_attrs.items():
            label = labels.get(aid)
            if label:
                attrs_json[label] = str(val)
        sku, _aviso = reservar_sku(
            data.get("sku") or "", produto_id, vid, base=base, conn=conn,
        )
        conn.execute(
            "UPDATE produtos_cadastro SET sku=?, atributos=? WHERE id=?",
            (sku, json.dumps(attrs_json, ensure_ascii=False), vid),
        )

    # Downloads de imagem ficam FORA da transação: não seguram o lock de
    # escrita durante requisições de rede (evita "database is locked"
    # para as outras escritas do sistema).
    imagens = _absolute_images(data.get("images") or [], data.get("final_url") or url)
    baixadas = 0
    erros = 0
    imagens_rows: list[str] = []
    for img_url in imagens:
        target = _baixar_imagem(produto_id, img_url, url_final)
        if target is None:
            erros += 1
            continue
        imagens_rows.append(target)
        baixadas += 1
    if imagens_rows:
        with system_conn() as conn:
            conn.executemany(
                "INSERT INTO imagens_produto (produto_id, filename, ordem)"
                " VALUES (?,?,?)",
                [
                    (produto_id, filename, i)
                    for i, filename in enumerate(imagens_rows)
                ],
            )

    return {
        "id": vid,
        "nome": base,
        "marca": marca,
        "familia": fname,
        "family_key": family_key,
        "imagens_baixadas": baixadas,
        "imagens_erros": erros,
    }
