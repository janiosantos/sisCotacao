"""Reestrutura categoria/subcategoria: `categoria` passa a guardar só o nível
raiz do breadcrumb e `subcategoria` a folha. Antes, `categoria` guardava o
caminho inteiro ("A > B"); a partir de agora o caminho completo é montado por
join (raiz > folha) apenas no momento de exibir.

OBS: no Postgres o schema já é normalizado (categoria_id/subcategoria_id) —
este script é obsoleto e não faz nada.

Uso:
    python reestruturar_categoria.py            # não faz nada (obsoleto)
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry", action="store_true", help="não grava nada")
    ap.parse_args()

    # No Postgres o schema já é normalizado (categoria_id/subcategoria_id).
    print("Schema já normalizado no Postgres (categorias/subcategorias). "
          "Este script é obsoleto — nada a fazer.")


if __name__ == "__main__":
    main()