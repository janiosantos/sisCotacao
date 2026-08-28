"""Busca de produtos por termo — ILIKE + pg_trgm (sem produtos_fts).

Foco na **descricao padronizada** (Nome + características + Marca). A entrada é
quebrada em palavras; a relevância é pela **cobertura** (quantas palavras do
termo a descricao contém):

- **1 palavra**: casa se a palavra estiver na descricao OU no sku/ean (busca
  por código). Ranking: descricao prefixo > sku/ean exato > contém.
- **2+ palavras**: exige texto completo na descricao OU **pelo menos 2 palavras**
  na descricao OU o código (sku/ean) contendo o texto completo — evita que
  "cabo flexivel azul" traga "Caixa Azul" (1/3). ORDER BY **cobertura DESC** →
  descricao prefixo → sku/ean exato → nome.
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


def _cobertura(alias: str, n: int) -> str:
    """Expressão SQL: nº de palavras do termo presentes na descricao."""
    return " + ".join(
        f"(CASE WHEN f_unaccent({alias}.descricao) ILIKE f_unaccent(?) THEN 1 ELSE 0 END)"
        for _ in range(n)
    )


def montar_busca(q: str, alias: str = "p") -> tuple[str, list, str, list]:
    """Monta (where_sql, where_params, order_expr, order_params).

    Os params são separados (WHERE × ORDER BY) porque a contagem usa só o WHERE.
    """
    toks = tokens(q)
    if not toks:
        return "1=1", [], "", []

    P = alias
    qpat = f"%{q}%"
    token_params = [f"%{t}%" for t in toks]
    N = len(toks)

    if N == 1:
        where_sql = (
            "("
            f"f_unaccent({P}.descricao) ILIKE f_unaccent(?)"
            f" OR f_unaccent({P}.sku) ILIKE f_unaccent(?)"
            f" OR f_unaccent({P}.ean) ILIKE f_unaccent(?)"
            ")"
        )
        where_params = [qpat, qpat, qpat]
        rank = (
            f"CASE"
            f" WHEN f_unaccent({P}.descricao) ILIKE f_unaccent(?) || '%' THEN 90"
            f" WHEN f_unaccent({P}.sku) = f_unaccent(?) THEN 85"
            f" WHEN f_unaccent({P}.ean) = f_unaccent(?) THEN 80"
            f" WHEN f_unaccent({P}.sku) ILIKE f_unaccent(?) || '%' THEN 70"
            f" WHEN f_unaccent({P}.descricao) ILIKE '%' || f_unaccent(?) || '%' THEN 60"
            f" ELSE 20 END"
        )
        order_params = [q, q, q, q, q]
        order_expr = f"{rank} DESC, {P}.nome COLLATE NOCASE, {P}.id"
        return where_sql, where_params, order_expr, order_params

    cov = _cobertura(P, N)
    # WHERE (2+ palavras): texto completo na descricao OU cobertura >= 2 OU código.
    where_sql = (
        "("
        f"f_unaccent({P}.descricao) ILIKE f_unaccent(?)"
        f" OR ({cov}) >= 2"
        f" OR f_unaccent({P}.sku) ILIKE f_unaccent(?)"
        f" OR f_unaccent({P}.ean) ILIKE f_unaccent(?)"
        ")"
    )
    where_params = [qpat] + token_params + [qpat, qpat]

    order_sql = (
        f"({cov}) DESC,"
        f"(CASE WHEN f_unaccent({P}.descricao) ILIKE f_unaccent(?) || '%' THEN 1 ELSE 0 END) DESC,"
        f"(CASE WHEN f_unaccent({P}.sku) = f_unaccent(?) THEN 1 ELSE 0 END) DESC,"
        f"(CASE WHEN f_unaccent({P}.ean) = f_unaccent(?) THEN 1 ELSE 0 END) DESC,"
        f"{P}.nome COLLATE NOCASE, {P}.id"
    )
    order_params = token_params + [q, q, q]
    return where_sql, where_params, order_sql, order_params