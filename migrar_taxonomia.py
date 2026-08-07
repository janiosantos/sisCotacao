"""Executa a migração consolidada em migrar_taxonomia.sql sobre amostra_estrutura.db.

A execução é feita comando-a-comando (e não executescript) para que as
PRAGMAs foreign_keys (que são no-op dentro de transação) sejam alternadas no
momento correto. Em caso de erro, a transação da fase de reconstrução (Passo 1.4)
é revertida com ROLLBACK e o estado original é preservado.
"""
from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

DB = "amostra_estrutura.db"
SQL_FILE = "migrar_taxonomia.sql"


def run() -> None:
    sql = Path(SQL_FILE).read_text(encoding="utf-8")
    # remove linhas de comentário para que ";" dentro delas não quebre o split
    src_lines = [l for l in sql.splitlines() if not l.lstrip().startswith("--")]
    stmts = [s.strip() for s in "\n".join(src_lines).split(";") if s.strip()]
    conn = sqlite3.connect(DB)
    conn.isolation_level = None  # autocommit: o script SQL controla BEGIN/COMMIT
    cur = conn.cursor()

    try:
        for stmt in stmts:
            cur_stmt = stmt
            cur.execute(stmt)
            print("ok:", stmt.splitlines()[0][:80])
    except sqlite3.Error as e:
        conn.rollback()
        print("FALHOU:", e)
        print("--- statement que falhou:")
        print(cur_stmt)
        print("ROLLBACK aplicado — banco mantido no estado anterior.")
        sys.exit(1)

    conn.commit()

    print("\n=== Validação final ===")
    for r in cur.execute(
        "PRAGMA foreign_key_check"
    ).fetchall():
        print("FK VIOLADA:", r)
    for r in cur.execute(
        """SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'categor%'"""
    ).fetchall():
        n = cur.execute(f"SELECT COUNT(*) FROM {r[0]}").fetchone()[0]
        print(f"{r[0]}: {n}")
    conn.close()
    print("\nMigração concluída sem erros.")


if __name__ == "__main__":
    run()