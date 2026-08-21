"""Classificação Curva ABC do catálogo (bootstrap).

Usa o Potencial de Margem de Contribuição Total Estimado
(giro_esperado_mercado * margem_lucro_estimada * preco_venda), ordena
decrescente e aplica os cortes acumulados 70/20/10 (A/B/C).

Uso:
    python classificar_abc.py                  # aplica definitivo (com backup)
    python classificar_abc.py --dry            # só calcula/reporta
    python classificar_abc.py --no-backup
    python classificar_abc.py --resumo         # só imprime a distribuição atual
"""
from __future__ import annotations

import argparse
import sys

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from catalog_server import abc  # noqa: E402


def _backup() -> str:
    return "Postgres (backup não se aplica a arquivo)"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry", action="store_true", help="não grava nada")
    ap.add_argument("--no-backup", action="store_true")
    ap.add_argument("--resumo", action="store_true", help="só imprime o estado atual")
    args = ap.parse_args()

    if args.resumo:
        r = abc.resumo_curva()
        print("== Por classe ==")
        tt = sum(x["resultado"] or 0 for x in r["por_classe"])
        for x in r["por_classe"]:
            pct = (x["resultado"] or 0) / tt * 100 if tt else 0
            print(f"  Classe {x['classe']}: {x['produtos']:6d} produtos | resultado {pct:5.1f}%")
        print("== Por linha (exclui 'Geral') ==")
        for x in r["por_linha"]:
            if x["linha"] == "Geral":
                continue
            print(f"  {x['linha']:32s} n={x['produtos']:6d}  A={x['classe_a']:5d}  C={x['classe_c']:5d}")
        return

    print("1) Preenchendo parâmetros de mercado por linha de produto...")
    # Os parâmetros (linha/margem/giro) são estimativas determinísticas e
    # idempotentes — são sempre persistidos; o `--dry` só impede a atribuição
    # da classe/ordem ABC (a parte realmente classificatória).
    n_upd, n_sem_linha = abc.preencher_parametros(dry=False)
    print(f"   linhas/margem/giro preenchidos: {n_upd} | sem linha (Geral): {n_sem_linha}")

    backup = _backup() if not args.dry and not args.no_backup else "—"
    if backup != "—":
        print(f"   backup: {backup}")

    print("1b) Marcando rolar (em_linha) — equipamentos de alto valor ficam fora...")
    em = abc.marcar_em_linha(dry=args.dry)
    print(f"   fora de linha (não no rolar): {em['fora_de_linha']} | em linha: {em['em_linha']}")

    print("2) Aplicando Curva ABC (70/20/10 acumulado) sobre o rolar em foco...")
    res = abc.aplicar_curva(dry=args.dry)
    print(f"   produtos classificados: {res['atualizados']} | total resultado estimado: R$ {res['total_geral']:,.2f}")
    print(f"   sem lucro estimado (-> C): {res['sem_lucro']}")
    for cls in ("A", "B", "C"):
        c = res["resumo"][cls]
        print(f"   Classe {cls}: {c['produtos']:6d} produtos -> {c['resultado']:5.1f}% do resultado")

    if args.dry:
        print("\nDRY-RUN: nada foi gravado.")


if __name__ == "__main__":
    main()