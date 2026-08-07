"""Reestrutura categoria/subcategoria: `categoria` passa a guardar só o nível
raiz do breadcrumb e `subcategoria` a folha. Antes, `categoria` guardava o
caminho inteiro ("A > B"); a partir de agora o caminho completo é montado por
join (raiz > folha) apenas no momento de exibir.

Uso:
    python reestruturar_categoria.py            # aplica definitivo (com backup)
    python reestruturar_categoria.py --dry      # só reporta
"""
from __future__ import annotations

import argparse
import shutil
import sys
import sqlite3
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from catalog_server.db import SYSTEM_DB  # noqa: E402


def _backup() -> str:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    dest = Path(SYSTEM_DB).with_name(f"server_backup_categoria_{ts}.db")
    shutil.copy2(SYSTEM_DB, dest)
    return str(dest)


def _separar(categoria: str, subcategoria: str) -> tuple[str, str]:
    """Ajusta categoria/subcategoria para (raiz, folha).

    - Se `categoria` guarda o caminho ("A > B > C"): raiz = 1º segmento e
      folha = último segmento (subcategoria é recalculado).
    - Se `categoria` já é só a raiz (sem '>'): mantem o `subcategoria`
      existente (que já é a folha); se vazia, usa a própria raiz.
    """
    if ">" in (categoria or ""):
        partes = [p.strip() for p in (categoria or "").split(">") if p.strip()]
        if partes:
            return partes[0], partes[-1]
    raiz = (categoria or "").strip()
    folha = (subcategoria or "").strip()
    return raiz, folha or raiz


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry", action="store_true", help="não grava nada")
    args = ap.parse_args()

    with sqlite3.connect(SYSTEM_DB, timeout=30) as conn:
        cols = {r[1] for r in conn.execute("PRAGMA table_info(produtos_cadastro)").fetchall()}
    if "categoria" not in cols:
        print("Schema já normalizado (categorias/subcategorias). Este script é "
              "obsoleto — nada a fazer.")
        return

    with sqlite3.connect(SYSTEM_DB, timeout=30) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT id, categoria, subcategoria FROM produtos_cadastro"
            " WHERE categoria IS NOT NULL AND categoria != ''"
        ).fetchall()

    mudados = 0
    amostras: list[tuple[str, str, str, str]] = []
    updates: list[tuple[str, str, int]] = []
    for r in rows:
        cat, sub = _separar(r["categoria"], r["subcategoria"])
        sub_antigo = r["subcategoria"] or ""
        if cat == (r["categoria"] or "").strip() and sub == sub_antigo.strip():
            continue
        mudados += 1
        updates.append((cat, sub, r["id"]))
        if len(amostras) < 8:
            amostras.append((r["categoria"], cat, sub_antigo, sub))

    if args.dry:
        print(f"DRY-RUN: {mudados} produtos seriam ajustados.")
    else:
        backup = _backup()
        print(f"backup: {backup}")
        print(f"aplicando {len(updates)} ajustes...")
        with sqlite3.connect(SYSTEM_DB, timeout=60) as w:
            w.executemany(
                "UPDATE produtos_cadastro SET categoria=?, subcategoria=?,"
                " atualizado_em=CURRENT_TIMESTAMP WHERE id=?",
                updates,
            )
        print("ok.")

    if amostras:
        print("amostras (antes -> raiz | sub_antiga -> folha):")
        for a in amostras:
            print(f"  ['{a[0]}'] -> cat=['{a[1]}'] | sub ['{a[2]}' -> '{a[3]}']")


if __name__ == "__main__":
    main()