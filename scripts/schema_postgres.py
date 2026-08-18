"""Gera o schema PostgreSQL equivalente ao SQLite do catálogo/cotações.

O schema final SQLite (87 tabelas, resultante das 52 migrações) é a fonte da
verdade. Este script conecta num banco SQLite com as migrations aplicadas,
converte cada `CREATE TABLE`/`CREATE INDEX` para o dialeto Postgres e grava um
único arquivo SQL pronto para o `psql`/`pg_dump` importar.

Conversões aplicadas:
- `INTEGER PRIMARY KEY AUTOINCREMENT`  -> `BIGSERIAL PRIMARY KEY`
- `REAL`                              -> `DOUBLE PRECISION`
- `BLOB`                              -> `BYTEA`
- `DEFAULT (datetime('now'))`         -> `DEFAULT (to_char(now(),'YYYY-MM-DD HH24:MI:SS'))`
  (mantém o formato de data-texto que o SQLite produzia)
- `COLLATE NOCASE` (só em índices)    -> removido (Postgres usa colação do banco)

Uso:
    .venv\\Scripts\\python.exe scripts\\schema_postgres.py            # gera scripts/postgres_schema.sql
    .venv\\Scripts\\python.exe scripts\\schema_postgres.py --db <path> # usa um sqlite existente
"""
from __future__ import annotations

import argparse
import re
import sqlite3
import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
if str(PROJECT) not in sys.path:
    sys.path.insert(0, str(PROJECT))
OUT_DEFAULT = PROJECT / "scripts" / "postgres_schema.sql"

_TYPE_MAP = {
    "INTEGER": "INTEGER",
    "REAL": "DOUBLE PRECISION",
    "TEXT": "TEXT",
    "BLOB": "BYTEA",
    "NUMERIC": "NUMERIC",
}

# Colunas declaradas INTEGER no SQLite que guardam texto (SQLite é de tipo
# dinâmico). No Postgres precisam ser TEXT — ex.: ID externo do scraper.
_OVERRIDE_TEXT = {"external_id": "TEXT"}

_DT_DEFAULT = re.compile(r"DEFAULT\s*\(\s*datetime\('now'\)\s*\)", re.IGNORECASE)
_PK_AUTO = re.compile(r"INTEGER\s+PRIMARY\s+KEY\s+AUTOINCREMENT", re.IGNORECASE)
# REFERENCES coluna(id) [ON DELETE ...] — extraído para ALTER TABLE no final.
# Pode haver tokens após o ON DELETE (ex.: "REFERENCES clientes(id)
# ON DELETE CASCADE UNIQUE"): captura o trecho REFERENCES...ON DELETE... e
# preserva o restante (UNIQUE) como constraint inline da coluna.
_REF = re.compile(
    r"\s+REFERENCES\s+(IF NOT EXISTS\s+)?([\w]+)\s*\(([\w]+)\)(\s+ON\s+(?:DELETE|UPDATE)\s+(?:CASCADE|RESTRICT|SET\s+NULL|SET\s+DEFAULT|NO\s+ACTION))?",
    re.IGNORECASE,
)


def _convert_column_type(decl: str) -> str:
    """Converte o tipo/declaração de uma coluna para Postgres."""
    # exceções de coluna que precisam ser TEXT mesmo declaradas INTEGER
    for override_col, pg_t in _OVERRIDE_TEXT.items():
        if re.match(rf"^\s*{override_col}\b", decl, re.IGNORECASE):
            decl = re.sub(r"\bINTEGER\b", pg_t, decl, count=1, flags=re.IGNORECASE)
    # substitui o PK autoincrement primeiro (tipo + restrição)
    if _PK_AUTO.search(decl):
        decl = _PK_AUTO.sub("BIGSERIAL PRIMARY KEY", decl)
    # demais tipos
    for sqlite_t, pg_t in _TYPE_MAP.items():
        # só casa palavra inteira (ex.: "INTEGER" != "INTEGER PRIMARY KEY ...")
        decl = re.sub(rf"\b{re.escape(sqlite_t)}\b", pg_t, decl, count=1)
    # default de data-texto
    decl = _DT_DEFAULT.sub("DEFAULT (to_char(now(),'YYYY-MM-DD HH24:MI:SS'))", decl)
    return decl


def _split_top_level(body: str) -> list[str]:
    """Divide o corpo do CREATE TABLE em definições no nível de profundidade 0.

    Respeita parênteses aninhados (CHECK com lista) e strings entre aspas
    simples (defaults com vírgula).
    """
    parts: list[str] = []
    depth = 0
    in_str = False
    cur: list[str] = []
    i = 0
    while i < len(body):
        ch = body[i]
        if in_str:
            cur.append(ch)
            if ch == "'":
                # aspas escapadas '''' ou \' ?
                if i + 1 < len(body) and body[i + 1] == "'":
                    cur.append(body[i + 1])
                    i += 1
                else:
                    in_str = False
        elif ch == "'":
            in_str = True
            cur.append(ch)
        elif ch == "(":
            depth += 1
            cur.append(ch)
        elif ch == ")":
            depth -= 1
            cur.append(ch)
        elif ch == "," and depth == 0:
            parts.append("".join(cur).strip())
            cur = []
        else:
            cur.append(ch)
        i += 1
    if cur:
        parts.append("".join(cur).strip())
    return [p for p in parts if p]


def _convert_create_table(sql: str) -> tuple[str, list[str]]:
    """Converte um CREATE TABLE e devolve (ddl, lista de FKs p/ ALTER TABLE)."""
    sql = sql.strip()
    if not sql.endswith(";"):
        sql += ";"
    # header CREATE TABLE (nome pode vir entre aspas duplas)
    header = re.match(r'CREATE TABLE\s+(IF NOT EXISTS\s+)?"?([\w]+)"?', sql, re.IGNORECASE)
    if not header:
        raise ValueError(f"CREATE TABLE não reconhecido: {sql[:80]}...")
    table = header.group(2)
    # extrai o bloco entre parênteses
    start = sql.index("(")
    # respeita parênteses aninhados (CHECK com lista etc.)
    depth = 0
    for i in range(start, len(sql)):
        if sql[i] == "(":
            depth += 1
        elif sql[i] == ")":
            depth -= 1
            if depth == 0:
                end = i
                break
    body = sql[start + 1 : end]

    lines = []
    fks: list[str] = []
    for line in _split_top_level(body):
        # linha de restrição de nível de tabela (não tem nas migrações, mas seguro)
        if re.match(r"^(PRIMARY|FOREIGN|UNIQUE|CHECK|CONSTRAINT)\b", line, re.IGNORECASE):
            lines.append(line)
            continue
        # extrai FK da coluna para ALTER TABLE (Postgres exige tabela-alvo existente)
        m = _REF.search(line)
        if m:
            local_col = line.split()[0]
            target = m.group(2)
            target_col = m.group(3)
            on_clause = (m.group(4) or "").strip()
            fk_name = f"fk_{table}_{local_col}"
            fk_sql = (
                f"ALTER TABLE {table} ADD CONSTRAINT {fk_name} FOREIGN KEY ({local_col})"
                f" REFERENCES {target}({target_col})"
                + (f" {on_clause}" if on_clause else "")
                + ";"
            )
            fks.append(fk_sql)
            # remove só o trecho REFERENCES..ON DELETE.., preserva sufixo (ex.: UNIQUE)
            line = line[: m.start()].rstrip() + " " + line[m.end() :].strip()
        lines.append(_convert_column_type(line))
    ddl = f"CREATE TABLE {table} (\n  " + ",\n  ".join(lines) + "\n);"
    return ddl, fks


def _convert_index(sql: str) -> str:
    sql = sql.strip()
    sql = re.sub(r"COLLATE\s+NOCASE", "", sql, flags=re.IGNORECASE)
    sql = re.sub(r"\s+", " ", sql)
    if not sql.endswith(";"):
        sql += ";"
    return sql


def build_schema(db_path: Path) -> str:
    conn = sqlite3.connect(db_path)
    try:
        rows = conn.execute(
            "SELECT type, name, sql FROM sqlite_master"
            " WHERE type IN ('table','index') AND sql IS NOT NULL"
            " AND name NOT LIKE 'sqlite_%' AND name != 'schema_migrations'"
            " ORDER BY CASE type WHEN 'table' THEN 0 ELSE 1 END, name"
        ).fetchall()
    finally:
        conn.close()

    out = [
        "-- Schema PostgreSQL equivalente ao SQLite do catálogo/cotações.",
        "-- Gerado por scripts/schema_postgres.py (fonte: 52 migrations).",
        "-- Tabelas primeiro (sem FKs), índices, e FKs via ALTER TABLE ao final",
        "-- para respeitar a ordem de criação no Postgres.",
        "",
    ]
    fks: list[str] = []
    for typ, _name, sql in rows:
        try:
            if typ == "table":
                ddl, table_fks = _convert_create_table(sql)
                out.append(ddl)
                fks.extend(table_fks)
            else:
                out.append(_convert_index(sql))
        except Exception as e:  # noqa: BLE001
            raise SystemExit(f"erro convertendo {_name}: {e}")
        out.append("")
    out.append("-- Foreign keys (após todas as tabelas existirem)")
    out.append("")
    out.extend(fks)
    out.append("")
    out.append("-- FTS5 (produtos_fts) é criado em runtime no SQLite e não entra aqui;")
    out.append("-- no Postgres será substituído por tsvector/pg_trgm numa etapa futura.")
    return "\n".join(out)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="scripts/schema_postgres.py")
    ap.add_argument("--db", default=None, help="SQLite com migrations aplicadas (default: gera banco temp)")
    ap.add_argument("--out", default=str(OUT_DEFAULT), help="arquivo SQL de saída")
    args = ap.parse_args(argv)

    if args.db:
        db_path = Path(args.db)
    else:
        import tempfile

        from catalog_server.migrations.runner import apply

        tmp = Path(tempfile.mktemp(suffix=".db"))
        apply(tmp)
        db_path = tmp

    sql = build_schema(db_path)
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(sql, encoding="utf-8")
    print(f"schema gerado: {out_path} ({len(sql)} bytes)")

    if args.db is None:
        db_path.unlink(missing_ok=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())