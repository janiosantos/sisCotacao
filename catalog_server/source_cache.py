"""Cache de páginas-fonte (HTML) baixadas de lojas, em BANCO DEDICADO.

O HTML cru é volumoso; para não inflar/degradar o banco do catálogo/ERP, ele é
guardado num arquivo separado (`server_cache.db`, ver `db.CACHE_DB`), na tabela
`paginas_fonte` (coluna `html`), indexado por URL. Assim, consultas futuras
(breadcrumb, preços, atributos) leem a fonte já salva sem rebaixar a página.
"""
from __future__ import annotations

import sqlite3
from urllib.parse import urlparse

from catalog_server.db import cache_conn


def _normalize(url: str) -> str:
    return (url or "").strip()


def _site(url: str) -> str:
    host = (urlparse(url).hostname or "sem-host").lower()
    return host[4:] if host.startswith("www.") else host


def buscar(url: str) -> str | None:
    """Devolve o HTML salvo para a URL (ou None se não estiver no cache)."""
    url = _normalize(url)
    if not url:
        return None
    try:
        with cache_conn() as conn:
            row = conn.execute(
                "SELECT html FROM paginas_fonte WHERE url=?", (url,)
            ).fetchone()
    except sqlite3.Error:
        return None
    return row["html"] if row else None


def existe(url: str) -> bool:
    url = _normalize(url)
    try:
        with cache_conn() as conn:
            return conn.execute(
                "SELECT 1 FROM paginas_fonte WHERE url=?", (url,)
            ).fetchone() is not None
    except sqlite3.Error:
        return False


def salvar(
    url: str,
    html: str,
    variante_id: int | None = None,
    produto_id: int | None = None,
    origem: str = "parse_url",
    url_final: str = "",
) -> bool:
    """Grava o HTML da página no banco de cache (upsert por URL)."""
    url = _normalize(url)
    if not url or not html:
        return False
    try:
        with cache_conn() as conn:
            conn.execute(
                """INSERT INTO paginas_fonte
                       (url, site, html, bytes, url_final, produto_id, variante_id, origem, atualizada_em)
                   VALUES (?,?,?,?,?,?,?,?, datetime('now'))
                   ON CONFLICT(url) DO UPDATE SET
                       html=excluded.html, bytes=excluded.bytes,
                       url_final=CASE WHEN excluded.url_final<>'' THEN excluded.url_final ELSE paginas_fonte.url_final END,
                       produto_id=excluded.produto_id, variante_id=excluded.variante_id,
                       origem=excluded.origem, atualizada_em=datetime('now')""",
                (url, _site(url), html, len(html), url_final, produto_id, variante_id, origem),
            )
        return True
    except sqlite3.Error:
        return False


def invalida(url: str) -> None:
    """Remove a URL do cache (força rebaixamento futuro)."""
    url = _normalize(url)
    try:
        with cache_conn() as conn:
            conn.execute("DELETE FROM paginas_fonte WHERE url=?", (url,))
    except sqlite3.Error:
        pass


def referenciar(url: str, produto_id: int | None = None, variante_id: int | None = None) -> None:
    """Vincula a página salva a um produto/variante do catálogo."""
    url = _normalize(url)
    if not url:
        return
    try:
        with cache_conn() as conn:
            conn.execute(
                "UPDATE paginas_fonte SET produto_id=COALESCE(?,produto_id),"
                " variante_id=COALESCE(?,variante_id) WHERE url=?",
                (produto_id, variante_id, url),
            )
    except sqlite3.Error:
        pass