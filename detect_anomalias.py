"""Detecta anomalias de preço nos dados do catálogo para revisão manual.

Não altera a base — apenas lê `server.db` e reporta suspeitas. Exemplo clássico:
a mesma Haste Magnética (mesmo EAN) com preços R$ 17 vs R$ 78 entre lojas, ou
dois cabos da MESMA bitola com preços R$ 7 vs R$ 42 — sinais de preço capturado
de um produto "relacionado" no site (quando o item real está sob consulta/esgotado).

Uso:
    python detect_anomalias.py                     # relatório no console
    python detect_anomalias.py --ratio 1.5          # razão mínima (padrão 1.5x)
    python detect_anomalias.py --csv anomalias.csv   # exporta também em CSV
    python detect_anomalias.py --json anomalias.json

Regras:
  1. Duplicidade por EAN: o mesmo EAN em 2+ variantes ativas -> o item físico é o
     mesmo; se a razão entre maior/menor preço passar do limite, é suspeito.
  2. Mesma bitola/diâmetro no mesmo produto: variantes do mesmo produtos_cadastro
     que compartilham a mesma bitola só deveriam diferir por cor/outros fatores
     sem grandes saltos de preço; razão além do limite indica captura errada.
"""
from __future__ import annotations

import argparse
import csv
import json
import unicodedata
from typing import Any

from catalog_server.config import DATABASE_URL
from catalog_server.db import SYSTEM_DB, system_conn

DB = str(SYSTEM_DB)
_IS_PG = bool(DATABASE_URL)

_BITOLA_KEYS = {"bitola", "diametro"}


def norm(s: str) -> str:
    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()


def is_bitola_attr(nome: str) -> bool:
    n = norm(nome)
    return any(k in n for k in _BITOLA_KEYS)


def _ratio(min_p: float, max_p: float) -> float:
    if min_p <= 0:
        return float("inf")
    return max_p / min_p


def ean_duplicatas(conn: Any, limite: float) -> list[dict]:
    rows = conn.execute(
        """
        SELECT v.ean, v.id AS variante_id, v.sku, v.preco, v.marca,
               p.id AS produto_id, p.nome
        FROM variantes v
        JOIN produtos_cadastro p ON p.id = v.produto_id
        WHERE v.ativo = 1 AND p.ativo = 1
          AND v.ean IS NOT NULL AND TRIM(v.ean) != ''
        ORDER BY v.ean, v.preco
        """
    ).fetchall()

    grupos: dict[str, list] = {}
    for r in rows:
        grupos.setdefault(r["ean"], []).append(r)

    out: list[dict] = []
    for ean, itens in grupos.items():
        if len(itens) < 2:
            continue
        precos = [i["preco"] for i in itens]
        r = _ratio(min(precos), max(precos))
        out.append(
            {
                "tipo": "ean",
                "ean": ean,
                "produto_id": itens[0]["produto_id"],
                "nome": itens[0]["nome"],
                "n": len(itens),
                "ratio": round(r, 2),
                "anomalia": r >= limite,
                "itens": [
                    {
                        "variante_id": i["variante_id"],
                        "sku": i["sku"],
                        "preco": i["preco"],
                        "marca": i["marca"],
                    }
                    for i in itens
                ],
            }
        )
    return out


def bitola_no_produto(conn: Any, limite: float) -> list[dict]:
    bitola_ids = [
        a["id"]
        for a in conn.execute("SELECT id, nome FROM familia_atributos").fetchall()
        if is_bitola_attr(a["nome"])
    ]
    if not bitola_ids:
        return []
    plc = ",".join("?" * len(bitola_ids))
    rows = conn.execute(
        f"""
        SELECT va.variante_id, va.valor AS bitola,
               v.sku, v.preco, p.id AS produto_id, p.nome
        FROM variante_atributos va
        JOIN variantes v ON v.id = va.variante_id
        JOIN produtos_cadastro p ON p.id = v.produto_id
        WHERE va.atributo_id IN ({plc})
          AND v.ativo = 1 AND p.ativo = 1
          AND v.preco > 0
        ORDER BY p.id, va.valor, v.preco
        """,
        bitola_ids,
    ).fetchall()

    grupos: dict[tuple, list] = {}
    for r in rows:
        k = (r["produto_id"], norm(r["bitola"]))
        grupos.setdefault(k, []).append(r)

    out: list[dict] = []
    for (pid, b), itens in grupos.items():
        if len(itens) < 2:
            continue
        precos = [i["preco"] for i in itens]
        r = _ratio(min(precos), max(precos))
        out.append(
            {
                "tipo": "bitola",
                "produto_id": pid,
                "nome": itens[0]["nome"],
                "bitola": itens[0]["bitola"],
                "n": len(itens),
                "ratio": round(r, 2),
                "anomalia": r >= limite,
                "itens": [
                    {
                        "variante_id": i["variante_id"],
                        "sku": i["sku"],
                        "preco": i["preco"],
                    }
                    for i in itens
                ],
            }
        )
    return out


def _fmt_br(v) -> str:
    try:
        return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except (TypeError, ValueError):
        return ""


def main() -> None:
    ap = argparse.ArgumentParser(description="Detecta anomalias de preço para revisão manual")
    ap.add_argument("--ratio", type=float, default=1.5, help="razão máximo/mínimo que aciona a anomalia (padrão 1.5)")
    ap.add_argument("--csv", default="", help="opcional: também exporta o relatório em CSV")
    ap.add_argument("--json", default="", help="opcional: também exporta o relatório em JSON")
    args = ap.parse_args()

    with system_conn() as conn:
        por_ean = ean_duplicatas(conn, args.ratio)
        por_bitola = bitola_no_produto(conn, args.ratio)

    todos = por_ean + por_bitola
    suspeitos = [g for g in todos if g["anomalia"]]

    print("=" * 78)
    print("ANOMALIAS DE PREÇO — revisão manual")
    print(f"Limite de razão: {args.ratio}x | base: {DB}" + (" (Postgres)" if _IS_PG else ""))
    print("=" * 78)

    def imprime_grupo(g):
        print()
        tag = "SUSPEITO" if g["anomalia"] else "informativo"
        print(f"[{tag}] {g['nome']}  (produto {g['produto_id']})")
        if g["tipo"] == "ean":
            print(f"      EAN {g['ean']} compartilhado por {g['n']} variante(s) · razão {g['ratio']}x")
        else:
            print(f"      bitola '{g['bitola']}' em {g['n']} variante(s) · razão {g['ratio']}x")
        for i in g["itens"]:
            print(f"      - var {i['variante_id']} sku {i['sku']}  {_fmt_br(i['preco'])}"
                  + (f"  ({i['marca']})" if i.get("marca") else ""))

    print(f"\n>> {len(suspeitos)} grupo(s) suspeito(s) de {len(todos)} analisado(s)")
    for g in todos:
        imprime_grupo(g)

    if args.csv:
        with open(args.csv, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["tipo", "nome", "produto_id", "chave", "n", "ratio", "anomalia", "variante_id", "sku", "preco"])
            for g in todos:
                for i in g["itens"]:
                    w.writerow([g["tipo"], g["nome"], g["produto_id"], g.get("ean", g.get("bitola")), g["n"], g["ratio"], g["anomalia"], i["variante_id"], i["sku"], i["preco"]])
        print(f"\nCSV exportado: {args.csv}")

    if args.json:
        with open(args.json, "w", encoding="utf-8") as f:
            json.dump(todos, f, ensure_ascii=False, indent=2)
        print(f"JSON exportado: {args.json}")


if __name__ == "__main__":
    main()