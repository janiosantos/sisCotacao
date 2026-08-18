"""Baseline quantitativo do banco (estado "antes da migração").

Gera um JSON/MD com contagem de linhas das tabelas e métricas de qualidade
dos dados de produto/variação (SKU/EAN duplicados, sem família, sem categoria,
etc.). Serve de referência para comparar depois da migração para PostgreSQL.

Uso:
    python scripts/baseline.py [--out baseline.json]
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from catalog_server.config import SYSTEM_DB


def _counts(conn: sqlite3.Connection) -> dict[str, int]:
    rows = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        " AND name NOT LIKE 'produtos_fts%' ORDER BY name"
    ).fetchall()
    out: dict[str, int] = {}
    for (name,) in rows:
        try:
            out[name] = conn.execute(f'SELECT COUNT(*) FROM "{name}"').fetchone()[0]
        except sqlite3.OperationalError:
            out[name] = None
    return out


def _quality(conn: sqlite3.Connection) -> dict:
    q = lambda s: conn.execute(s).fetchone()[0]  # noqa: E731
    return {
        "produtos_cadastro": q("SELECT COUNT(*) FROM produtos_cadastro"),
        "variantes": q("SELECT COUNT(*) FROM variantes"),
        "variantes_sem_sku": q(
            "SELECT COUNT(*) FROM variantes WHERE sku IS NULL OR TRIM(sku)=''"
        ),
        "variantes_sem_ean": q(
            "SELECT COUNT(*) FROM variantes WHERE ean IS NULL OR TRIM(ean)=''"
        ),
        "skus_duplicados_grupos": q(
            "SELECT COUNT(*) FROM (SELECT sku FROM variantes"
            " WHERE sku IS NOT NULL AND TRIM(sku)<>'' GROUP BY sku HAVING COUNT(*)>1)"
        ),
        "eans_duplicados_grupos": q(
            "SELECT COUNT(*) FROM (SELECT ean FROM variantes"
            " WHERE ean IS NOT NULL AND TRIM(ean)<>'' GROUP BY ean HAVING COUNT(*)>1)"
        ),
        "produtos_sem_familia": q(
            "SELECT COUNT(*) FROM produtos_cadastro WHERE familia_id IS NULL"
        ),
        "produtos_sem_categoria": q(
            "SELECT COUNT(*) FROM produtos_cadastro WHERE categoria_id IS NULL"
        ),
        "produtos_sem_variantes": q(
            "SELECT COUNT(*) FROM produtos_cadastro p WHERE NOT EXISTS"
            " (SELECT 1 FROM variantes v WHERE v.produto_id=p.id)"
        ),
        "variantes_inativas": q("SELECT COUNT(*) FROM variantes WHERE ativo=0"),
        "estoque_saldo_total": q(
            "SELECT COALESCE(SUM(quantidade),0) FROM estoque_saldo"
        ),
        "estoque_movimento": q("SELECT COUNT(*) FROM estoque_movimento"),
        "fiscal_config": q("SELECT COUNT(*) FROM fiscal_config"),
        "familia_atributos": q("SELECT COUNT(*) FROM familia_atributos"),
        "variante_atributos": q("SELECT COUNT(*) FROM variante_atributos"),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Baseline quantitativo do banco")
    ap.add_argument("--out", type=Path, default=Path("baseline.json"))
    args = ap.parse_args()

    if not SYSTEM_DB.exists():
        print(f"banco não encontrado: {SYSTEM_DB}")
        return 1

    conn = sqlite3.connect(f"file:{SYSTEM_DB.resolve().as_posix()}?mode=ro", uri=True)
    try:
        user_version = conn.execute("PRAGMA user_version").fetchone()[0]
        baseline = {
            "gerado_em": datetime.now().isoformat(timespec="seconds"),
            "user_version": user_version,
            "tabela": _counts(conn),
            "qualidade_produtos": _quality(conn),
        }
    finally:
        conn.close()

    args.out.write_text(
        json.dumps(baseline, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"baseline salvo em: {args.out.resolve()}")
    print(
        "resumo: "
        + json.dumps(baseline["qualidade_produtos"], ensure_ascii=False)
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())