"""Busca de produtos por termo — ILIKE + pg_trgm (sem produtos_fts).

Foco na **descricao padronizada** (Nome + características + Marca): a entrada do
usuário é quebrada em palavras e a busca casa se **qualquer** palavra OU o
**texto digitado por inteiro** aparecer na descricao — busca por "qualquer
palavra". SKU/EAN também são considerados (busca por código). Ranking prioriza
descricao que começa com o termo e códigos exatos.
"""
from __future__ import annotations

import re

_TOKEN_RE = re.compile(r"[0-9A-Za-z\u00C0-\u00D6\u00D8-\u00F6\u00F8-\u00FF.,]+")


def tokens(q: str) -> list[str]:
    out: list[str] = []
    for t in _TOKEN_RE.findall(q or ""):
        t = t.strip(".,")
        if t:
            out.append(t)
    return out


def montar_busca(q: str, alias: str = "p") -> tuple[str, list, str, list]:
    """Monta (where_sql, where_params, order_expr, order_params).

    - WHERE (OR): texto completo na descricao/sku/ean OU qualquer palavra na
      descricao — `f_unaccent(campo) ILIKE f_unaccent('%<palavra>%')`.
    - order_expr: CASE de relevância (descricao prefixo > sku/ean exatos >
      prefixo de código > descricao contém > nome prefixo > demais).

    Os params são separados (WHERE × ORDER BY) porque a contagem usa só o WHERE.
    """
    toks = tokens(q)
    if not toks:
        return "1=1", [], "", []

    P = alias
    qpat = f"%{q}%"

    # WHERE — OR sobre descricao (texto completo + palavras) e código (sku/ean).
    ors = [
        f"f_unaccent({P}.descricao) ILIKE f_unaccent(?)",
        f"f_unaccent({P}.sku) ILIKE f_unaccent(?)",
        f"f_unaccent({P}.ean) ILIKE f_unaccent(?)",
    ]
    where_params: list = [qpat, qpat, qpat]
    for t in toks:
        ors.append(f"f_unaccent({P}.descricao) ILIKE f_unaccent(?)")
        where_params.append(f"%{t}%")
    where_sql = "(" + " OR ".join(ors) + ")"

    t0 = toks[0]
    rank = (
        f"CASE"
        f" WHEN f_unaccent({P}.descricao) ILIKE f_unaccent(?) || '%' THEN 90"
        f" WHEN f_unaccent({P}.sku) = f_unaccent(?) THEN 85"
        f" WHEN f_unaccent({P}.ean) = f_unaccent(?) THEN 80"
        f" WHEN f_unaccent({P}.sku) ILIKE f_unaccent(?) || '%' THEN 70"
        f" WHEN f_unaccent({P}.descricao) ILIKE '%' || f_unaccent(?) || '%' THEN 60"
        f" WHEN f_unaccent({P}.nome) ILIKE f_unaccent(?) || '%' THEN 50"
        f" ELSE 20 END"
    )
    order_params = [q, q, q, q, q, t0]
    order_expr = f"{rank} DESC, {P}.nome COLLATE NOCASE, {P}.id"
    return where_sql, where_params, order_expr, order_params