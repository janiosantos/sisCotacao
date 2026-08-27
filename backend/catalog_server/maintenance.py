"""Tarefas de manutenção do catálogo (produção), executadas via self-hosted runner.

Uso (dentro do container backend):
    python -m catalog_server.maintenance <tarefa>

Tarefas:
    health               Resumo do estado do catálogo (contagens).
    padronizar_descricoes Recompõe a descricao padronizada (Nome + atributos +
                         Marca) de todos os produtos — idempotente.
    normalizar_subcategorias Mescla subcategorias duplicadas dentro da mesma
                         categoria (variação de caixa/acento/espaços) e
                         reaponta os produtos — idempotente.

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


def normalizar_subcategorias(conn) -> None:
    """Mescla subcategorias duplicadas dentro da mesma categoria.

    Duplicatas são variações de caixa/acento/espaços do mesmo nome (ex.:
    "Chave De Roda" vs "Chave de Roda"). Mantém a de mais produtos (desempate
    por id menor), reaponta os produtos e apaga as demais. Idempotente.
    """
    cur = conn.execute(
        "SELECT id, categoria_id, nome,"
        " btrim(regexp_replace(lower(f_unaccent(nome)), '\\s+', ' ', 'g')) AS chave"
        " FROM subcategorias"
    )
    groups: dict[tuple, list] = {}
    for r in cur.fetchall():
        groups.setdefault((r["categoria_id"], r["chave"]), []).append(r)

    mescladas = 0
    movidos = 0
    for (_cid, _chave), rows in groups.items():
        if len(rows) < 2:
            continue
        keep = rows[0]
        best = -1
        for r in rows:
            n = conn.execute(
                "SELECT count(*) FROM produtos_cadastro WHERE subcategoria_id=?",
                (r["id"],),
            ).fetchone()[0]
            if n > best or (n == best and r["id"] < keep["id"]):
                keep, best = r, n
        for r in rows:
            if r["id"] == keep["id"]:
                continue
            up = conn.execute(
                "UPDATE produtos_cadastro SET subcategoria_id=? WHERE subcategoria_id=?",
                (keep["id"], r["id"]),
            )
            movidos += up.rowcount if up.rowcount and up.rowcount > 0 else 0
            conn.execute("DELETE FROM subcategorias WHERE id=?", (r["id"],))
            mescladas += 1
    print(f"subcategorias mescladas: {mescladas} | produtos reapontados: {movidos}")


TASKS = {
    "health": health,
    "padronizar_descricoes": padronizar_descricoes,
    "normalizar_subcategorias": normalizar_subcategorias,
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