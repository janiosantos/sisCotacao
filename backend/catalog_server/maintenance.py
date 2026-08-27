"""Tarefas de manutenção do catálogo (produção), executadas via self-hosted runner.

Uso (dentro do container backend):
    python -m catalog_server.maintenance <tarefa>

Tarefas:
    health           Resumo do estado do catálogo (contagens).
    diagnose_search  Valida que produtos com atributos retornam na busca FTS.
    fts_rebuild      Reconstrói produtos_fts a partir das tabelas base
                     (índice derivado/regenerável — não altera dados de origem).

A execução em produção é disparada pelo workflow `.github/workflows/maintenance.yml`
(`workflow_dispatch`, input `task`), que roda no runner `siscom-prod` dentro do
container `backend` — sem necessidade de `scp` manual.
"""
from __future__ import annotations

import sys

from catalog_server import fts
from catalog_server.db import system_conn


def health(conn) -> None:
    prods = conn.execute("SELECT count(*) AS c FROM produtos_cadastro").fetchone()["c"]
    variants = conn.execute("SELECT count(*) AS c FROM produtos_cadastro").fetchone()["c"]
    fts_rows = conn.execute("SELECT count(*) AS c FROM produtos_fts").fetchone()["c"]
    with_attrs = conn.execute(
        "SELECT count(*) AS c FROM produtos_fts "
        "WHERE atributos IS NOT NULL AND atributos <> ''"
    ).fetchone()["c"]
    print("produtos_cadastro :", prods)
    print("produtos          :", variants)
    print("produtos_fts      :", fts_rows)
    print("produtos_fts+atr  :", with_attrs)


def diagnose_search(conn) -> None:
    with_attrs = conn.execute(
        "SELECT count(*) AS c FROM produtos_fts "
        "WHERE atributos IS NOT NULL AND atributos <> ''"
    ).fetchone()["c"]
    print("produtos_fts com atributos (populados):", with_attrs)

    rows = conn.execute(
        "SELECT produto_id, atributos FROM produtos_fts "
        "WHERE atributos IS NOT NULL AND atributos <> '' LIMIT 15"
    ).fetchall()

    falhas = 0
    for r in rows:
        pid = r["produto_id"]
        atributos = r["atributos"]
        token = None
        for w in atributos.replace("²", "").split():
            if len(w) >= 3 and any(c.isalpha() for c in w):
                token = w
                break
        if not token:
            continue
        match = fts.search_query(token)
        hit = conn.execute(
            "SELECT 1 FROM produtos_fts WHERE produto_id=? AND produtos_fts MATCH ?",
            (pid, match),
        ).fetchone()
        status = "OK" if hit else "FALHOU"
        if not hit:
            falhas += 1
        print("  pid=%d token=%r -> %s" % (pid, token, status))
    print("Falhas: %d / %d" % (falhas, len(rows)))


def fts_rebuild(conn) -> None:
    fts.rebuild(conn)
    n = conn.execute("SELECT count(*) AS c FROM produtos_fts").fetchone()["c"]
    print("produtos_fts reconstruído:", n, "linhas")


TASKS = {
    "health": health,
    "diagnose_search": diagnose_search,
    "fts_rebuild": fts_rebuild,
}


def main(argv) -> int:
    if len(argv) < 2 or argv[1] not in TASKS:
        print("Tarefas disponíveis: " + ", ".join(TASKS))
        return 2
    with system_conn() as conn:
        TASKS[argv[1]](conn)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
