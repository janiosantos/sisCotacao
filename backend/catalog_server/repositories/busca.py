"""Busca de produtos por termo — ILIKE + pg_trgm (sem produtos_fts).

Gera cláusulas WHERE/ORDER BY com ranking de relevância, insensível a acentos
via `f_unaccent`. Campos pesquisados: nome, marca, sku, ean, termos_busca,
descricao (etiqueta padronizada com as características embutidas), família,
categoria e subcategoria.

Aliases assumidos na consulta: `p` = produtos_cadastro, `f` = familias,
`cat` = categorias, `sub` = subcategorias (todas como LEFT JOIN quando usadas).
"""
from __future__ import annotations

import re

_TOKEN_RE = re.compile(r"[0-9A-Za-z\u00C0-\u00D6\u00D8-\u00F6\u00F8-\u00FF.,]+")

# Campos pesquisados (a descricao carrega as características; f/cat/sub são os joins).
_CAMPOS = [
    "{p}.nome", "{p}.marca", "{p}.sku", "{p}.ean", "{p}.termos_busca",
    "{p}.descricao", "f.nome", "cat.nome", "sub.nome",
]


def tokens(q: str) -> list[str]:
    out: list[str] = []
    for t in _TOKEN_RE.findall(q or ""):
        t = t.strip(".,")
        if t:
            out.append(t)
    return out


def montar_busca(q: str, alias: str = "p") -> tuple[str, list, str, list]:
    """Monta (where_sql, where_params, order_expr, order_params) para busca por termo.

    - WHERE: AND por token; cada token casa em qualquer campo pesquisado.
    - order_expr: expressão de ORDER BY (SEM o prefixo "ORDER BY") — CASE de
      relevância (sku/ean exatos > prefixos > contém > demais) + desempate por nome.

    Os params são separados (WHERE × ORDER BY) porque a contagem de resultados
    usa apenas o WHERE.
    """
    toks = tokens(q)
    if not toks:
        return "1=1", [], "", []

    campos = [c.format(p=alias) for c in _CAMPOS]
    where_clauses: list[str] = []
    where_params: list = []
    for t in toks:
        pat = f"%{t}%"
        ors = " OR ".join(f"f_unaccent({c}) ILIKE f_unaccent(?)" for c in campos)
        where_clauses.append(f"({ors})")
        where_params += [pat] * len(campos)

    t0 = toks[0]
    P = alias
    rank = (
        f"CASE"
        f" WHEN f_unaccent({P}.sku) = f_unaccent(?) THEN 100"
        f" WHEN f_unaccent({P}.ean) = f_unaccent(?) THEN 95"
        f" WHEN f_unaccent({P}.nome) ILIKE f_unaccent(?) || '%' THEN 80"
        f" WHEN f_unaccent({P}.sku) ILIKE f_unaccent(?) || '%' THEN 70"
        f" WHEN f_unaccent({P}.descricao) ILIKE f_unaccent(?) || '%' THEN 60"
        f" WHEN f_unaccent({P}.nome) ILIKE '%' || f_unaccent(?) || '%' THEN 50"
        f" WHEN f_unaccent({P}.descricao) ILIKE '%' || f_unaccent(?) || '%' THEN 40"
        f" WHEN f_unaccent({P}.marca) ILIKE '%' || f_unaccent(?) || '%'"
        f" OR f_unaccent(f.nome) ILIKE '%' || f_unaccent(?) || '%'"
        f" OR f_unaccent(cat.nome) ILIKE '%' || f_unaccent(?) || '%'"
        f" OR f_unaccent(sub.nome) ILIKE '%' || f_unaccent(?) || '%'"
        f" OR f_unaccent({P}.termos_busca) ILIKE '%' || f_unaccent(?) || '%' THEN 20"
        f" ELSE 0 END"
    )
    order_params = [t0] * 12
    order_expr = f"{rank} DESC, {P}.nome COLLATE NOCASE, {P}.id"
    return " AND ".join(where_clauses), where_params, order_expr, order_params