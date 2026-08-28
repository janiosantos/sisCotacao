"""Imagens em lote — busca no fornecedor, preview e atribuição a produtos.

Fluxo (produtos sem imagem, ex.: fios):
1. `buscar_fornecedor(url)` — busca a página de busca do fornecedor e devolve
   os links candidatos de produto (nome + thumbnail).
2. `preview_imagens(url)` — busca a página do produto e devolve as URLs de
   imagem candidatas (priorizando a melhor resolução), sem baixar.
3. `baixar_lote(produto_ids, urls, repo)` — baixa cada imagem (uma vez) e
   atribui a todos os produtos do lote, com dedup por conteúdo (MD5).
4. `irmaos(conn, produto_id)` — encontra os "irmãos" do produto (mesmo nome,
   mesma marca e mesma cor — variando a bitola) para montar o lote.

Fornecedores suportados (busca): casadosparafusos, anhangueraferramentas,
casadoeletricistasc (extração genérica de cards de produto + parsers).
"""
from __future__ import annotations

import hashlib
import re
from urllib.parse import urljoin, urlparse

import requests

from catalog_server.services import imagens_service

_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/138.0 Safari/537.36"
)
_HEADERS = {"User-Agent": _UA, "Accept-Language": "pt-BR,pt;q=0.9"}

# Caminhos que não são de produto (busca, conta, institucional etc.).
_SKIP_PATH = re.compile(
    r"/(busca|procura|carrinho|login|conta|minha-conta|checkout|ajuda|sobre|"
    r"contato|blog|noticia|politica|privacidade|termos|categorias?|catalog|"
    r"marcas?|fale-conosco|quem-somos|como-comprar|venda-atacado|favoritos|"
    r"wishlist|lista|central|atendimento|garantia|troca|devolucao)(/|$)",
    re.I,
)


def _reg_domain(host: str) -> str:
    """Domínio registrado (ex.: casadoeletricistasc.com.br, casadosparafusos.com)."""
    labels = host.split(".")
    if len(labels) >= 3 and labels[-2] in ("com", "gov", "net", "org") and len(labels[-1]) == 2:
        return ".".join(labels[-3:])
    return ".".join(labels[-2:]) if len(labels) >= 2 else host


def _fetch_html(url: str) -> tuple[str, str]:
    """Baixa o HTML e devolve (html, url_final). Com 1 retry em timeout/5xx."""
    session = requests.Session()
    session.headers.update(_HEADERS)
    for tentativa in range(2):
        try:
            resp = session.get(url, timeout=30)
            if resp.status_code >= 500:
                if tentativa == 0:
                    continue
            resp.raise_for_status()
            return resp.text, resp.url
        except requests.Timeout:
            if tentativa == 0:
                continue
            raise
        except requests.RequestException:
            if tentativa == 0 and resp.status_code >= 500:
                continue
            raise
    raise requests.RequestException(f"falha ao acessar {url}")


def _thumb_from_img(tag: str) -> str:
    m = re.search(r'(?:src|data-src)\s*=\s*["\']([^"\']+)["\']', tag, re.I)
    return m.group(1) if m else ""


def buscar_fornecedor(url: str) -> list[dict]:
    """Busca a página de busca do fornecedor e extrai os cards de produto.

    Preferência por cards `<a><img>` (thumb do produto) — o padrão do
    casadoeletricistasc (principal fonte de cabos/fios). Sites renderizados via
    JS (anhanguera/casadosparafusos) podem não expor os links no HTML estático;
    nesse caso o usuário cola a URL do produto diretamente no passo seguinte.
    """
    html, final_url = _fetch_html(url)
    base = final_url or url
    reg = _reg_domain((urlparse(base).hostname or "").lower())

    cards: dict[str, dict] = {}
    for m in re.finditer(
        r'<a[^>]*href=["\']([^"\']+)["\'][^>]*>(.*?)</a>',
        html,
        re.S | re.I,
    ):
        href = (m.group(1) or "").strip()
        inner = m.group(2)
        if not href or href.startswith(("#", "javascript:", "mailto:", "tel:")):
            continue
        full = urljoin(base, href)
        cand_host = (urlparse(full).hostname or "").lower()
        if not cand_host or _reg_domain(cand_host) != reg or cand_host.startswith("checkout."):
            continue
        path = urlparse(full).path
        if _SKIP_PATH.search(path) or len(path) < 8:
            continue
        # Card de produto tem <img> (thumb) OU caminho /p/<slug> (casadosparafusos).
        img = re.search(r"<img[^>]*>", inner, re.I)
        if not img and not re.search(r"/p/[^/]+", path):
            continue
        if full in cards:
            continue
        name = ""
        thumb = ""
        if img:
            tag = img.group(0)
            alt = re.search(r'alt\s*=\s*["\']([^"\']*)["\']', tag, re.I)
            title = re.search(r'title\s*=\s*["\']([^"\']*)["\']', tag, re.I)
            name = (alt.group(1) if alt else "") or (title.group(1) if title else "")
            thumb = urljoin(base, _thumb_from_img(tag))
        if not name:
            text = re.sub(r"<[^>]+>", " ", inner)
            name = re.sub(r"\s+", " ", text).strip()
        if not name:
            continue
        cards[full] = {
            "url": full,
            "name": re.sub(r"\s+", " ", name).strip()[:120],
            "thumb": thumb,
        }
    return list(cards.values())[:40]


_TINY_PATH = re.compile(
    r"/(tiny|media|mini|thumb|min|small|medium|icon|ico)(/|[-._])|[-._]\d{2,4}x\d{2,4}\b|\.svg$",
    re.I,
)
# Caminhos claramente não-produto (banners, config, frete etc.).
_NAO_PRODUTO = re.compile(
    r"/(barra_|config/|banner|logo|frete|selo|icone|icons?/|bg_|topo_|rodape|"
    r"favicon|whats|pagamento|marketing|campanha)",
    re.I,
)


def preview_imagens(url: str) -> list[dict]:
    """Extrai e VALIDA as fotos de uma página de produto (melhor resolução).

    Baixa cada candidata (com 1 retry), descarta miniaturas/banners/config e
    **deduplica por conteúdo (MD5)** — a mesma foto aparece em URLs diferentes
    (og:image, srcset, src). Devolve apenas fotos distintas, baixáveis e com
    dimensões/tamanho, limitado a 20.
    """
    html, final_url = _fetch_html(url)
    urls = imagens_service._extract_image_urls(html, final_url or url)
    ok = [u for u in urls if not _TINY_PATH.search(u) and not _NAO_PRODUTO.search(u)]
    produtos = [u for u in ok if "/produtos/" in u or "/produto/" in u]
    candidatas = (produtos or ok)[:30]

    session = requests.Session()
    session.headers.update(_HEADERS)
    por_md5: dict[str, dict] = {}
    for u in candidatas:
        try:
            r = _baixar(session, u, referer=final_url or url)
            ctype = r.headers.get("Content-Type", "")
            if not (ctype.startswith("image/") or imagens_service._is_direct_image(u)):
                continue
            size = imagens_service._image_size(r.content)
            if size and max(size) < imagens_service._MIN_DIMENSION:
                continue
            md5 = hashlib.md5(r.content).hexdigest()
            if md5 in por_md5:
                continue  # mesma foto, URL diferente
            por_md5[md5] = {
                "url": u,
                "md5": md5,
                "largura": size[0] if size else None,
                "altura": size[1] if size else None,
                "size_kb": round(len(r.content) / 1024),
            }
        except Exception:
            continue
    return list(por_md5.values())[:20]


def _baixar(session, url: str, referer: str = "", tentativas: int = 1) -> requests.Response:
    """GET com retry em timeout/5xx. `tentativas` = retries extras além da 1ª."""
    headers = {"Referer": referer} if referer else {}
    ultimo: Exception | None = None
    for i in range(tentativas + 1):
        try:
            r = session.get(url, timeout=30, headers=headers)
            if r.status_code >= 500 and i < tentativas:
                continue
            r.raise_for_status()
            return r
        except (requests.Timeout, requests.RequestException) as exc:
            ultimo = exc
            if i >= tentativas:
                break
    raise ultimo if ultimo else requests.RequestException(f"falha ao baixar {url}")


def baixar_lote(
    produto_ids: list[int],
    urls: list[str],
    favorita_url: str = "",
    repo=None,
) -> dict:
    """Baixa cada imagem (com retry) e atribui a todos os produtos do lote.

    - Limites: até 20 produtos e 20 imagens por lote.
    - Dedup por conteúdo (MD5) **por produto** (a mesma foto pode ir para
      vários produtos; não duplica dentro do mesmo produto).
    - A foto **favorita** vira a capa (ordem 0) em cada produto.
    Devolve {aplicadas, erros, por_produto}.
    """
    if repo is None:
        from catalog_server.repositories import produto_repo as _r

        repo = _r
    if len(produto_ids) > 20:
        return {"aplicadas": 0, "erros": ["Limite de 20 produtos por lote"], "por_produto": {}}
    urls = [u.strip() for u in urls if u and u.strip()]
    if len(urls) > 20:
        return {"aplicadas": 0, "erros": ["Limite de 20 imagens por lote"], "por_produto": {}}

    session = requests.Session()
    session.headers.update(_HEADERS)
    aplicadas = 0
    deduplicadas = 0
    erros: list[str] = []
    por_produto: dict[int, int] = {pid: 0 for pid in produto_ids}
    fav_ids: dict[int, int] = {}

    for u in urls:
        try:
            r = _baixar(session, u, referer=u, tentativas=1)
            ctype = r.headers.get("Content-Type", "")
            if not (ctype.startswith("image/") or imagens_service._is_direct_image(u)):
                erros.append(f"{u}: não é imagem")
                continue
            size = imagens_service._image_size(r.content)
            if size and max(size) < imagens_service._MIN_DIMENSION:
                erros.append(f"{u}: imagem muito pequena")
                continue
        except Exception as exc:
            erros.append(f"{u}: {exc}")
            continue
        for pid in produto_ids:
            if imagens_service._conteudo_duplicado(pid, r.content):
                deduplicadas += 1  # foto já existente neste produto
                continue
            target = imagens_service._save_bytes(pid, u, r.content)
            img_id = repo.add_imagem(pid, str(target), url_origem=u)
            aplicadas += 1
            por_produto[pid] = por_produto.get(pid, 0) + 1
            if u == favorita_url:
                fav_ids[pid] = img_id

    # Foto favorita -> capa (ordem 0) em cada produto.
    if favorita_url:
        for pid, img_id in fav_ids.items():
            try:
                repo.set_imagem_capa(pid, img_id)
            except Exception:
                pass
    return {
        "aplicadas": aplicadas,
        "deduplicadas": deduplicadas,
        "erros": erros,
        "por_produto": por_produto,
    }


def irmaos(conn, produto_id: int) -> list[dict]:
    """Irmãos do produto: mesmo nome + mesma marca + mesma cor (a bitola varia).

    Usado para montar o lote de imagens de fios/cabos que diferem só pela bitola.
    """
    row = conn.execute(
        "SELECT nome, marca, atributos FROM produtos_cadastro WHERE id=?",
        (produto_id,),
    ).fetchone()
    if row is None:
        return []
    nome = row["nome"] or ""
    marca = row["marca"] or ""
    atributos = row["atributos"] or {}
    cor = str(atributos.get("Cor") or "").strip()

    rows = conn.execute(
        "SELECT id, nome, marca, sku, descricao, atributos FROM produtos_cadastro"
        " WHERE ativo=1 AND id<>? AND f_unaccent(lower(nome))=f_unaccent(lower(?))"
        "   AND f_unaccent(lower(marca))=f_unaccent(lower(?))"
        " ORDER BY id",
        (produto_id, nome, marca),
    ).fetchall()
    out: list[dict] = []
    for r in rows:
        attrs = r["atributos"] or {}
        if cor and f_unaccent_lower(attrs.get("Cor")) != f_unaccent_lower(cor):
            continue
        out.append({
            "id": r["id"],
            "nome": r["nome"],
            "marca": r["marca"] or "",
            "sku": r["sku"] or "",
            "descricao": (r["descricao"] or "").strip(),
            "atributos": {k: str(v) for k, v in attrs.items()},
        })
    return out


def f_unaccent_lower(v) -> str:
    import unicodedata

    if v is None:
        return ""
    s = unicodedata.normalize("NFD", str(v))
    return "".join(c for c in s if unicodedata.category(c) != "Mn").lower().strip()