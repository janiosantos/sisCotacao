"""Tarefas de manutenção do catálogo (produção), executadas via self-hosted runner.

Uso (dentro do container backend):
    python -m catalog_server.maintenance <tarefa>

Tarefas:
    health               Resumo do estado do catálogo (contagens).
    padronizar_descricoes Recompõe a descricao padronizada (Nome + atributos +
                         Marca) de todos os produtos — idempotente.

A execução em produção é disparada pelo workflow `.github/workflows/maintenance.yml`
(`workflow_dispatch`, input `task`), que roda no runner `siscom-prod` dentro do
container `backend` — sem necessidade de `scp` manual.
"""
from __future__ import annotations

import sys

from catalog_server.db import system_conn

_DESCRICAO_SQL = [
    # Produtos com atributos (na ordem da família).
    """
    WITH attrs AS (
        SELECT p.id AS produto_id,
               string_agg(kv.value, ' ' ORDER BY fa.ordem, fa.id) AS vals
        FROM produtos_cadastro p
        JOIN familia_atributos fa ON fa.familia_id = p.familia_id
        JOIN jsonb_each_text(p.atributos) kv ON kv.key = fa.nome
        WHERE kv.value <> ''
        GROUP BY p.id
    )
    UPDATE produtos_cadastro p
    SET descricao = btrim(
        coalesce(p.nome, '')
        || CASE WHEN a.vals IS NOT NULL AND a.vals <> ''
                THEN ' ' || a.vals ELSE '' END
        || CASE WHEN btrim(coalesce(p.marca, '')) <> ''
                THEN ' - ' || btrim(p.marca) ELSE '' END)
    FROM attrs a
    WHERE a.produto_id = p.id
    """,
    # Demais (sem atributos/família): Nome - Marca.
    """
    UPDATE produtos_cadastro p
    SET descricao = btrim(
        coalesce(p.nome, '')
        || CASE WHEN btrim(coalesce(p.marca, '')) <> ''
                THEN ' - ' || btrim(p.marca) ELSE '' END)
    WHERE NOT EXISTS (
        SELECT 1
        FROM familia_atributos fa
        JOIN jsonb_each_text(p.atributos) kv ON kv.key = fa.nome
        WHERE fa.familia_id = p.familia_id AND kv.value <> ''
    )
    """,
]


def padronizar_descricoes(conn) -> None:
    for sql in _DESCRICAO_SQL:
        conn.execute(sql)
    n = conn.execute(
        "SELECT count(*) AS c FROM produtos_cadastro"
        " WHERE btrim(coalesce(descricao, '')) <> ''"
    ).fetchone()["c"]
    print("descricoes padronizadas:", n)


def health(conn) -> None:
    prods = conn.execute("SELECT count(*) AS c FROM produtos_cadastro").fetchone()["c"]
    ativos = conn.execute(
        "SELECT count(*) AS c FROM produtos_cadastro WHERE ativo=1"
    ).fetchone()["c"]
    com_desc = conn.execute(
        "SELECT count(*) AS c FROM produtos_cadastro"
        " WHERE btrim(coalesce(descricao, '')) <> ''"
    ).fetchone()["c"]
    print("produtos_cadastro :", prods)
    print("produtos ativos   :", ativos)
    print("com descricao     :", com_desc)


TASKS = {
    "health": health,
    "padronizar_descricoes": padronizar_descricoes,
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