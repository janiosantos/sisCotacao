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
    reclassificar_cabos  Corrige cabos elétricos ("Cabo Energia ... Flex ...
                         750V" e "Cabo Flex/Flexível") classificados como
                         Ferramentas, movendo para ELE / Fios e Cabos
                         Elétricos / Cabo Flexível 750V; normaliza "Conheça
                         Cabo Flex" (nome/descrição) — idempotente.

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


def reclassificar_cabos(conn) -> None:
    """Corrige cabos elétricos classificados como Ferramentas.

    Cabos elétricos ("Cabo Energia Pvc/cobre Flex ... 750V", "Cabo Flex",
    "Cabo Flexível") e os "Conheça Cabo Flex" (mesma família de SKU 55xxx)
    caíram em FER/Ferramentas. Move para ELE / Fios e Cabos Elétricos /
    subcategoria "Cabo Flexível 750V" e normaliza os "Conheça Cabo Flex"
    (nome/descrição). Idempotente.
    """
    g = conn.execute("SELECT id FROM grupos WHERE codigo='ELE'").fetchone()
    if not g:
        print("grupo ELE não existe; nada a fazer")
        return
    grupo_id = int(g["id"])
    subgrupo_id = int(conn.execute(
        "SELECT id FROM subgrupos WHERE grupo_id=? AND codigo='CAB'", (grupo_id,)
    ).fetchone()["id"])
    cat = conn.execute(
        "SELECT id FROM categorias WHERE nome='Fios e Cabos Elétricos'"
    ).fetchone()
    if not cat:
        print("categoria 'Fios e Cabos Elétricos' não existe")
        return
    cat_id = int(cat["id"])
    sub = conn.execute(
        "SELECT id FROM subcategorias WHERE categoria_id=? AND nome='Cabo Flexível 750V'",
        (cat_id,),
    ).fetchone()
    if not sub:
        print("subcategoria 'Cabo Flexível 750V' não existe")
        return
    sub_id = int(sub["id"])

    # f_unaccent remove acentos/cedilha — o padrão usa a forma sem acento.
    detect = "f_unaccent(lower(nome)) ~ '^cabo energia|^cabo flex|^conheca cabo flex'"
    rows = conn.execute(
        f"SELECT id, nome FROM produtos_cadastro WHERE grupo_id <> ? AND ({detect})",
        (grupo_id,),
    ).fetchall()
    print(f"cabos a reclassificar: {len(rows)}")
    for r in rows[:15]:
        print(f"  id={r['id']} | {r['nome'][:55]}")

    # Normaliza os "Conheça Cabo Flex" (nomes suspeitos -> cabo real).
    conn.execute(
        "UPDATE produtos_cadastro"
        " SET nome='Cabo Flexível 750V', descricao='Cabo Flexível 750V - SIL'"
        " WHERE f_unaccent(lower(nome)) ~ '^conheca cabo flex'"
    )
    # Reclassifica para ELE / Fios e Cabos Elétricos / Cabo Flexível 750V.
    cur = conn.execute(
        "UPDATE produtos_cadastro"
        " SET categoria_id=?, subcategoria_id=?, grupo_id=?, subgrupo_id=?"
        f" WHERE grupo_id <> ? AND ({detect})",
        (cat_id, sub_id, grupo_id, subgrupo_id, grupo_id),
    )
    print("reclassificados:", cur.rowcount)


TASKS = {
    "health": health,
    "padronizar_descricoes": padronizar_descricoes,
    "normalizar_subcategorias": normalizar_subcategorias,
    "reclassificar_cabos": reclassificar_cabos,
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