"""Serviço de imagens do cadastro de produtos.

- Salva uploads diretos em `images/cadastro/<produto_id>/`.
- Baixa imagens a partir de uma URL da internet: se for URL de página de
  produto, o serviço busca o HTML e extrai as fotos (og:image + <img>);
  se for URL direta de imagem, baixa direto.
"""
from __future__ import annotations

import hashlib
import re
import shutil
import uuid
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests

from catalog_server.config import IMAGES_DIR
from catalog_server.services.safe_http import get_public

_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/138.0 Safari/537.36"
)

_IMG_EXT = (".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".avif")


def _folder(produto_id: int) -> Path:
    return IMAGES_DIR / "cadastro" / str(produto_id)


_MIN_DIMENSION = 300  # ignora miniaturas menores que 300px no maior lado

_THUMB_PATTERNS = re.compile(
    r"(/(?:thumbs?|mini)/|[-._/](?:thumb|min|mini|small|medium|icon|ico|sprite)"
    r"[-._]|[-._]\d{2,3}x\d{2,3}\b|\.svg$)",
    re.I,
)

# Elementos de "chapeu" do site (banners, logos, selos): nunca são fotos do produto.
_JUNK_PATTERNS = re.compile(
    r"/(?:banners?_lateral|banners?|logos?|tema|badges?|selos?|icones?|icons?|sprites?|ckeditor)"
    r"(?:/|[-_.])|(?:loja[-_.]?segura|logo|badge|selo)[-_.]|/common/images/",
    re.I,
)


def _is_direct_image(url: str) -> bool:
    path = urlparse(url).path.lower()
    return path.endswith(_IMG_EXT)


def _is_thumbnail_url(url: str) -> bool:
    return bool(_THUMB_PATTERNS.search(urlparse(url).path))


def _is_junk_url(url: str) -> bool:
    return bool(_JUNK_PATTERNS.search(urlparse(url).path))


def _best_srcset(srcset: str) -> str:
    """Escolhe a entrada do srcset com a maior largura declarada."""
    best, best_w = None, -1
    for part in srcset.split(","):
        part = part.strip()
        if not part:
            continue
        tokens = part.split()
        url = tokens[0].strip()
        w = -1
        if len(tokens) > 1:
            m = re.match(r"(\d+)[wW]?", tokens[1])
            if m:
                w = int(m.group(1))
            elif url and best is None:
                best = url
        if w > best_w:
            best, best_w = url, w
    return best or ""


def _extract_image_urls(html: str, base_url: str) -> list[str]:
    """Extrai URLs de imagem priorizando alta resolução.

    Ordem de qualidade: og:image/twitter:image > srcset (maior largura) >
    src/data-src. URLs que claramente são miniaturas são colocadas por último
    (baixadas apenas se não houver opção melhor).
    """
    meta: list[str] = []
    for m in re.finditer(
        r'<meta[^>]+(?:property|name)\s*=\s*["\'](?:og:image|twitter:image)(?::[^"\']*)?'
        r'["\'][^>]*content\s*=\s*["\']([^"\']+)["\']',
        html,
        re.I,
    ):
        meta.append(m.group(1).strip())

    srcset_urls: list[str] = []
    src_urls: list[str] = []
    for m in re.finditer(r"<img[^>]*>", html, re.I):
        tag = m.group(0)
        ss = re.search(r'srcset\s*=\s*["\']([^"\']+)["\']', tag, re.I)
        if ss and ss.group(1).strip():
            best = _best_srcset(ss.group(1))
            if best:
                srcset_urls.append(best.strip())
        src = re.search(
            r'(?:src|data-src|data-lazy-src|data-original)\s*=\s*["\']([^"\']+)["\']',
            tag,
            re.I,
        )
        if src:
            src_urls.append(src.group(1).strip())

    def to_full(u: str) -> str | None:
        if not u or u.startswith("data:"):
            return None
        return urljoin(base_url, u)

    # Prioridade: meta > srcset > src. Miniaturas claras ficam por último;
    # URLs de "chapeu" do site (banners/logos/selos) são descartadas.
    ordered: list[tuple[str, bool]] = []
    for u in meta:
        f = to_full(u)
        if f and not _is_junk_url(f):
            ordered.append((f, False))
    for u in srcset_urls:
        f = to_full(u)
        if f and not _is_junk_url(f):
            ordered.append((f, _is_thumbnail_url(f)))
    for u in src_urls:
        f = to_full(u)
        if f and not _is_junk_url(f):
            ordered.append((f, _is_thumbnail_url(f)))

    ordered.sort(key=lambda item: item[1])
    seen: set[str] = set()
    out: list[str] = []
    for full, _ in ordered:
        if full in seen:
            continue
        seen.add(full)
        out.append(full)
    return out[:15]


def _image_size(content: bytes) -> tuple[int, int] | None:
    """Lê as dimensões (w, h) de PNG/JPEG/GIF/WebP direto do cabeçalho."""
    if content.startswith(b"\x89PNG\r\n\x1a\n") and len(content) >= 24:
        w = int.from_bytes(content[16:20], "big")
        h = int.from_bytes(content[20:24], "big")
        return (w, h) if w and h else None
    if content.startswith(b"\xff\xd8\xff") and len(content) >= 32:
        i = 2
        while i + 9 < len(content):
            if content[i] != 0xFF:
                i += 1
                continue
            marker = content[i + 1]
            if marker in (0xD8, 0xD9) or 0xD0 <= marker <= 0xD7:
                i += 2
                continue
            length = int.from_bytes(content[i + 2 : i + 4], "big")
            if marker in (0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF):
                h = int.from_bytes(content[i + 5 : i + 7], "big")
                w = int.from_bytes(content[i + 7 : i + 9], "big")
                return (w, h) if w and h else None
            i += 2 + length
        return None
    if content[:6] in (b"GIF87a", b"GIF89a") and len(content) >= 10:
        w = int.from_bytes(content[6:8], "little")
        h = int.from_bytes(content[8:10], "little")
        return (w, h) if w and h else None
    if content[:4] == b"RIFF" and content[8:12] == b"WEBP":
        if content[12:16] == b"VP8 " and len(content) >= 30:
            w = int.from_bytes(content[26:28], "little") & 0x3FFF
            h = int.from_bytes(content[28:30], "little") & 0x3FFF
            return (w, h) if w and h else None
        if content[12:16] == b"VP8L" and content[16] == 0x2F and len(content) >= 21:
            bits = int.from_bytes(content[17:21], "little")
            w = (bits & 0x3FFF) + 1
            h = ((bits >> 14) & 0x3FFF) + 1
            return (w, h) if w and h else None
        if content[12:16] == b"VP8X" and len(content) >= 30:
            w = int.from_bytes(content[24:27], "little") + 1
            h = int.from_bytes(content[27:30], "little") + 1
            return (w, h) if w and h else None
    return None


def _conteudo_duplicado(produto_id: int, content: bytes) -> bool:
    """True se o produto já possui uma imagem com o mesmo conteúdo (MD5).

    A mesma foto costuma aparecer em URLs diferentes (thumb/full, srcset);
    a dedup por URL não a pega. Compara o hash do conteúdo com os arquivos
    já salvos da pasta do produto.
    """
    folder = _folder(produto_id)
    if not folder.exists():
        return False
    novo = hashlib.md5(content).hexdigest()
    for f in folder.iterdir():
        if f.is_file():
            try:
                if hashlib.md5(f.read_bytes()).hexdigest() == novo:
                    return True
            except OSError:
                continue
    return False


def _relpath(produto_id: int, name: str) -> str:
    """Caminho RELATIVO ao IMAGES_DIR (ex.: cadastro/62470/foto.jpg)."""
    return (Path("cadastro") / str(produto_id) / name).as_posix()


def _save_bytes(produto_id: int, url: str, content: bytes) -> str:
    folder = _folder(produto_id)
    folder.mkdir(parents=True, exist_ok=True)
    basename = re.sub(r"[^A-Za-z0-9._-]", "_", Path(urlparse(url).path).name)
    suffix = Path(basename).suffix.lower()
    if suffix not in _IMG_EXT:
        suffix = ".jpg"
    digest = hashlib.md5(url.encode("utf-8")).hexdigest()[:10]
    target = folder / f"img_{digest}{suffix}"
    if not target.exists():
        target.write_bytes(content)
    # Retorna o caminho RELATIVO ao IMAGES_DIR (portátil).
    return _relpath(produto_id, target.name)


def salvar_uploads(produto_id: int, files, repo) -> list[str]:
    folder = _folder(produto_id)
    folder.mkdir(parents=True, exist_ok=True)
    saved: list[str] = []
    for f in files:
        if not f or not f.filename:
            continue
        ext = Path(f.filename).suffix.lower()
        if ext not in _IMG_EXT:
            ext = ".jpg"
        target = folder / f"upload_{uuid.uuid4().hex[:12]}{ext}"
        f.save(target)
        rel = _relpath(produto_id, target.name)
        repo.add_imagem(produto_id, rel)
        saved.append(rel)
    return saved


def salvar_conteudo_galeria(
    produto_id: int,
    content: bytes,
    extension: str,
    digest: str,
    gallery_image_id: int,
) -> str | None:
    """Salva uma imagem validada da galeria, sem confiar em caminho externo."""
    if _conteudo_duplicado(produto_id, content):
        return None
    folder = _folder(produto_id)
    folder.mkdir(parents=True, exist_ok=True)
    extension = extension if extension in _IMG_EXT else ".jpg"
    name = f"galeria_{gallery_image_id}_{digest[:12]}{extension}"
    target = folder / name
    target.write_bytes(content)
    relative = _relpath(produto_id, name)
    return relative


def baixar_de_url(produto_id: int, url: str, repo) -> tuple[list[dict], list[str]]:
    """Baixa imagens de uma URL (página de produto ou imagem direta).

    Retorna (baixadas, erros).
    """
    url = (url or "").strip()
    if not url:
        return [], ["Informe uma URL."]
    baixadas: list[dict] = []
    erros: list[str] = []
    session = requests.Session()
    session.headers.update({"User-Agent": _UA, "Accept-Language": "pt-BR,pt;q=0.9"})

    try:
        if _is_direct_image(url):
            candidates = [url]
        else:
            resp = get_public(url, timeout=30, headers=dict(session.headers), max_bytes=5 * 1024 * 1024)
            resp.raise_for_status()
            ctype = resp.headers.get("Content-Type", "")
            if ctype.startswith("image/"):
                candidates = [url]
            else:
                candidates = _extract_image_urls(resp.text, resp.url)
                if not candidates:
                    return [], ["Nenhuma imagem encontrada na página."]
    except Exception as exc:
        return [], [f"Não foi possível acessar a URL: {exc}"]

    ignoradas = 0
    for u in candidates:
        try:
            r = get_public(
                u,
                timeout=30,
                headers={"Referer": url, **dict(session.headers)},
                max_bytes=10 * 1024 * 1024,
            )
            r.raise_for_status()
            ctype = r.headers.get("Content-Type", "")
            if not (ctype.startswith("image/") or _is_direct_image(u)):
                continue
            size = _image_size(r.content)
            if size and max(size) < _MIN_DIMENSION:
                ignoradas += 1
                continue
            if _conteudo_duplicado(produto_id, r.content):
                ignoradas += 1  # mesma foto já existente (URL diferente)
                continue
            target = _save_bytes(produto_id, u, r.content)
            repo.add_imagem(produto_id, target)
            baixadas.append({"filename": target})
        except Exception as exc:
            erros.append(f"{u}: {exc}")
    if not baixadas and ignoradas:
        erros.append(f"{ignoradas} imagem(ns) muito pequena(s) ignorada(s) (menos de {_MIN_DIMENSION}px).")
    return baixadas, erros


def remover_arquivo(filename: str) -> None:
    try:
        p = Path(filename)
        if not p.is_absolute():
            p = IMAGES_DIR / p  # filename relativo ao IMAGES_DIR
        if p.is_file():
            p.unlink()
    except OSError:
        pass


def copiar_imagens(origem_id: int, destino_id: int, repo) -> list[str]:
    """Copia os arquivos de imagem de um produto para outro (duplicação).

    Preserva a ordem/capa do original: as cópias são adicionadas na mesma
    ordem (o `add_imagem` atribui `ordem` crescente a partir de 0, então a
    primeira cópia vira a capa). Os arquivos são copiados com nomes novos
    (`copia_<uuid>`) para não colidir com o produto de origem.
    """
    origem = repo.get_product(origem_id)
    if not origem:
        return []
    folder_src = _folder(origem_id)
    folder_dst = _folder(destino_id)
    if not folder_src.exists():
        return []
    folder_dst.mkdir(parents=True, exist_ok=True)
    copiadas: list[str] = []
    for im in origem.get("imagens") or []:
        filename = im.get("filename") or ""
        if not filename:
            continue
        src = Path(filename)
        if not src.is_absolute():
            src = IMAGES_DIR / src
        if not src.is_file():
            continue
        ext = src.suffix.lower()
        if ext not in _IMG_EXT:
            ext = ".jpg"
        novo_nome = f"copia_{uuid.uuid4().hex[:12]}{ext}"
        shutil.copy2(src, folder_dst / novo_nome)
        rel = _relpath(destino_id, novo_nome)
        repo.add_imagem(destino_id, rel)
        copiadas.append(rel)
    return copiadas


def remover_arquivos_produto(produto_id: int) -> None:
    folder = _folder(produto_id)
    if folder.exists():
        shutil.rmtree(folder, ignore_errors=True)
