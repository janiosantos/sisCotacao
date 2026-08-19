"""Gera um banco de amostra para demonstração/revisão de estrutura.

Cria `amostra_estrutura.db` (na raiz do projeto) com o SCHEMA COMPLETO do
catálogo/ERP (todas as tabelas, índices e o FTS5) e apenas alguns registros
representativos, mantendo a integridade referencial (pais antes dos filhos).

O objetivo é permitir que um analista avalie a modelagem sem carregar os
~8 GB do banco real.

Uso:
    python gerar_amostra_db.py
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

from catalog_server.config import SYSTEM_DB

OUT = Path(__file__).resolve().parent / "amostra_estrutura.db"

# (tabela, query de amostragem) — sem produtos/variantes/imagens, que são
# tratados com referência cruzada abaixo.
_SAMPLES: dict[str, str] = {
    "fornecedores": "SELECT * FROM fornecedores ORDER BY id LIMIT 3",
    "familias": "SELECT * FROM familias WHERE id IN ({ids}) ORDER BY id",
    "familia_atributos": "SELECT * FROM familia_atributos WHERE familia_id IN ({ids}) ORDER BY id LIMIT 15",
    "cotacoes": "SELECT * FROM cotacoes ORDER BY id LIMIT 2",
    "scraper_sync": "SELECT * FROM scraper_sync",
}

_EXCLUDE = {"sqlite_%", "produtos_fts", "produtos_fts_%"}


def _tables(conn: sqlite3.Connection) -> list[tuple[str, str]]:
    rows = conn.execute(
        "SELECT name, sql FROM sqlite_master"
        " WHERE type='table' AND sql IS NOT NULL"
        " ORDER BY name"
    ).fetchall()
    out = []
    for name, sql in rows:
        if any(name.startswith(e.replace("%", "")) for e in _EXCLUDE):
            continue
        out.append((name, sql))
    return out


def _indexes(conn: sqlite3.Connection) -> list[str]:
    return [
        r[1]
        for r in conn.execute(
            "SELECT name, sql FROM sqlite_master"
            " WHERE type='index' AND sql IS NOT NULL AND name NOT LIKE 'sqlite_%'"
            " ORDER BY name"
        ).fetchall()
    ]


def _cols(conn: sqlite3.Connection, table: str) -> list[str]:
    return [r[1] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()]


def _insert(conn: sqlite3.Connection, table: str, rows: list[tuple]) -> None:
    if not rows:
        return
    cols = _cols(conn, table)
    placeholders = ",".join("?" * len(cols))
    conn.executemany(
        f"INSERT INTO {table} ({','.join(cols)}) VALUES ({placeholders})", rows
    )


def _fetch(conn: sqlite3.Connection, sql: str, params: tuple = ()) -> list[tuple]:
    conn.row_factory = sqlite3.Row
    return [tuple(r) for r in conn.execute(sql, params).fetchall()]


def main() -> None:
    if OUT.exists():
        OUT.unlink()
    src = sqlite3.connect(SYSTEM_DB, timeout=30)

    dst = sqlite3.connect(OUT)
    dst.executescript("PRAGMA foreign_keys = ON;")

    # 1) DDL completo (tabelas + índices)
    for name, sql in _tables(src):
        dst.execute(sql)
    for idx in _indexes(src):
        dst.execute(idx)

    # 2) Amostra de famílias e produtos com variedade de linhas ABC
    produtos = _fetch(
        src,
        "SELECT * FROM produtos_cadastro"
        " GROUP BY linha_produto, classe_abc ORDER BY linha_produto, classe_abc LIMIT 12",
    )
    pcols = [c[1] for c in src.execute("PRAGMA table_info(produtos_cadastro)")]
    fam_id_col = pcols.index("familia_id")
    fam_ids = sorted({p[fam_id_col] for p in produtos if p[fam_id_col]}) if produtos else []

    _insert(dst, "familias", _fetch(src, _SAMPLES["familias"].format(ids=",".join(map(str, fam_ids)))))
    _insert(dst, "fornecedores", _fetch(src, _SAMPLES["fornecedores"]))
    _insert(dst, "produtos_cadastro", produtos)
    _insert(
        dst,
        "familia_atributos",
        _fetch(src, _SAMPLES["familia_atributos"].format(ids=",".join(map(str, fam_ids)))),
    )

    prod_ids = [p[0] for p in produtos]

    # 3) Variações e detalhes dos produtos amostrados
    variantes = _fetch(
        src,
        f"SELECT * FROM variantes WHERE produto_id IN ({','.join(map(str, prod_ids))})"
        " AND ativo=1 ORDER BY produto_id, id LIMIT 30",
    )
    _insert(dst, "variantes", variantes)
    var_ids = [v[0] for v in variantes]

    if var_ids:
        _insert(
            dst,
            "variante_atributos",
            _fetch(
                src,
                f"SELECT * FROM variante_atributos WHERE variante_id IN ({','.join(map(str, var_ids))})"
                " ORDER BY id LIMIT 25",
            ),
        )
    _insert(
        dst,
        "imagens_produto",
        _fetch(
            src,
            f"SELECT * FROM imagens_produto WHERE produto_id IN ({','.join(map(str, prod_ids))})"
            " ORDER BY id LIMIT 15",
        ),
    )

    # 4) Cotações (pais antes dos filhos)
    cotacoes = _fetch(src, _SAMPLES["cotacoes"])
    _insert(dst, "cotacoes", cotacoes)
    cot_ids = [c[0] for c in cotacoes]
    if cot_ids:
        sel = ",".join(map(str, cot_ids))
        cf = _fetch(src, f"SELECT * FROM cotacao_fornecedores WHERE cotacao_id IN ({sel}) ORDER BY id LIMIT 6")
        _insert(dst, "cotacao_fornecedores", cf)
        ci = _fetch(src, f"SELECT * FROM cotacao_itens WHERE cotacao_id IN ({sel}) ORDER BY id LIMIT 8")
        _insert(dst, "cotacao_itens", ci)
        ci_ids = [i[0] for i in ci]
        if ci_ids:
            _insert(
                dst,
                "cotacao_precos",
                _fetch(
                    src,
                    f"SELECT * FROM cotacao_precos WHERE cotacao_item_id IN ({','.join(map(str, ci_ids))})"
                    " ORDER BY id LIMIT 10",
                ),
            )
            _insert(
                dst,
                "pedido_itens",
                _fetch(
                    src,
                    f"SELECT * FROM pedido_itens WHERE cotacao_item_id IN ({','.join(map(str, ci_ids))})"
                    " ORDER BY id LIMIT 6",
                ),
            )

    _insert(dst, "scraper_sync", _fetch(src, _SAMPLES["scraper_sync"]))

    # 5) FTS5 do catálogo (recriado só com os produtos amostrados)
    from catalog_server import fts as fts_mod

    fts_mod.ensure_fts(dst)
    if prod_ids:
        rows = _fetch(
            src,
            f"{fts_mod._SELECT_FOR_INDEX} WHERE p.id IN ({','.join(map(str, prod_ids))})",
        )
        for r in rows:
            dst.execute(
                f"INSERT INTO {fts_mod._FTS}(produto_id, nome, marca, descricao, familia, skus, termos_busca)"
                " VALUES (?,?,?,?,?,?,?)",
                r,
            )

    # 6) paginas_fonte: mantém apenas o schema (sem dados do cache)
    pass

    dst.commit()

    # relatório
    total = 0
    print(f"criado: {OUT} ({OUT.stat().st_size/1024:.0f} KB)")
    for (t,) in dst.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"):
        try:
            n = dst.execute(f"SELECT COUNT(*) FROM \"{t}\"").fetchone()[0]
        except sqlite3.OperationalError:
            continue
        total += n
        print(f"  {t:24s} {n}")
    print(f"  {'TOTAL (linhas)':24s} {total}")

    dst.close()
    src.close()


if __name__ == "__main__":
    main()