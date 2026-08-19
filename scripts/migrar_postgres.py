"""Migra os dados do SQLite (catálogo/cotações + crawler) para o PostgreSQL.

Fluxo:
1. Conecta no SQLite (default: `catalog_server/data/server.db`) e no Postgres
   (`--pg-url`; default: lê `DATABASE_URL` do ambiente).
2. Opcionalmente aplica o baseline + migrações pendentes via runner PG
   (`scripts.pg_migrations`; o baseline usa `scripts/postgres_schema.sql`) antes
   do import (`--apply-schema`).
3. Desativa as FKs no Postgres (`session_replication_role=replica`), copia
   cada tabela em lotes de 5000 linhas, reativa as FKs e ajusta as sequences
   (`setval`) para o maior id importado.
4. Confere a contagem de linhas de cada tabela entre origem e destino.
5. Se o banco do scraper (`--crawler-db`; default `database/crawler.db`)
   existir, aplica o schema das tabelas do scraper e migra os dados também.

Uso:
    .venv\\Scripts\\python.exe scripts\\migrar_postgres.py                # server.db real
    .venv\\Scripts\\python.exe scripts\\migrar_postgres.py --db <path>    # banco específico
    .venv\\Scripts\\python.exe scripts\\migrar_postgres.py --apply-schema
    .venv\\Scripts\\python.exe scripts\\migrar_postgres.py --no-crawler   # não migra crawler.db
    .venv\\Scripts\\python.exe scripts\\migrar_postgres.py --pg-url postgresql+psycopg://...
"""
from __future__ import annotations

import argparse
import os
import sqlite3
import sys
from pathlib import Path

import psycopg
from psycopg.rows import dict_row

PROJECT = Path(__file__).resolve().parent.parent
if str(PROJECT) not in sys.path:
    sys.path.insert(0, str(PROJECT))

from catalog_server.config import CATALOG_DB, SYSTEM_DB  # noqa: E402

from app.database.schema_pg import (  # noqa: E402
    PRODUCT_ATTRIBUTES_PG_CREATE,
    SCRAPER_PG_CREATE,
)

BATCH = 5000

# Tabelas virtuals FTS5 (SQLite) sem equivalente direto em Postgres: a busca
# será substituída por tsvector/pg_trgm numa etapa futura. Não migram dados.
TABELAS_SKIP = {"produtos_fts", "produtos_fts_config", "produtos_fts_content",
                "produtos_fts_data", "produtos_fts_docsize", "produtos_fts_idx"}


def pg_dsn(url: str) -> str:
    """Converte postgresql+psycopg:// para o DSN aceito pelo psycopg3."""
    if url.startswith("postgresql+psycopg://"):
        return url.replace("postgresql+psycopg://", "postgresql://", 1)
    return url


def listar_tabelas(sq: sqlite3.Connection) -> list[str]:
    rows = sq.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
        " AND name NOT LIKE 'sqlite_%' AND name != 'schema_migrations' ORDER BY name"
    ).fetchall()
    return [r[0] for r in rows if r[0] not in TABELAS_SKIP]


def aplicar_schema_scraper(pg: psycopg.Connection) -> None:
    """Cria as tabelas do scraper no Postgres (idempotente)."""
    print("[schema] criando tabelas do scraper ...")
    pg.autocommit = True
    with pg.cursor() as cur:
        for stmt in SCRAPER_PG_CREATE + PRODUCT_ATTRIBUTES_PG_CREATE:
            cur.execute(stmt)
    pg.autocommit = False
    print("[schema] scraper OK")


def aplicar_schema_runner(pg_url: str, schema_file: Path | None = None) -> None:
    """Aplica o baseline + migrações pendentes via runner PG."""
    from scripts.pg_migrations import runner as pgm

    if schema_file is not None:
        pgm.SCHEMA_FILE = Path(schema_file)
    print(f"[schema] aplicando baseline + migrações ({pgm.SCHEMA_FILE}) ...")
    applied = pgm.apply(pg_url)
    print(f"[schema] versões aplicadas: {applied}")
    print("[schema] OK")


def copiar_tabela(
    sq: sqlite3.Connection, pg: psycopg.Connection, nome: str
) -> int:
    cols_sqlite = [r[1] for r in sq.execute(f"PRAGMA table_info({nome})")]
    cols = [c for c in cols_sqlite if c]
    if not cols:
        return 0
    col_sql = ", ".join(f'"{c}"' for c in cols)
    placeholders = ", ".join(["%s"] * len(cols))
    insert = f'INSERT INTO "{nome}" ({col_sql}) VALUES ({placeholders})'

    count = 0
    with pg.cursor() as pcur:
        for row in sq.execute(f"SELECT * FROM {nome}"):
            pcur.execute(insert, list(row))
            count += 1
            if count % BATCH == 0:
                print(f"  {nome}: {count} ...")
        # commit a cada tabela
    pg.commit()
    return count


def ajustar_sequences(pg: psycopg.Connection, tabelas: list[str]) -> None:
    """Faz setval das sequences das colunas id para o maior valor importado."""
    for nome in tabelas:
        with pg.cursor() as cur:
            # só ajusta se a tabela tiver coluna id (senão pg_get_serial_sequence falha)
            has_id = cur.execute(
                "SELECT 1 FROM information_schema.columns"
                " WHERE table_schema='public' AND table_name=%s AND column_name='id'",
                (nome,),
            ).fetchone()
            if not has_id:
                continue
            row = cur.execute(
                "SELECT pg_get_serial_sequence(%s, 'id') AS seq", (nome,)
            ).fetchone()
            if not row or not row["seq"]:
                continue
            seq = row["seq"]
            maxrow = cur.execute(
                f'SELECT COALESCE(MAX("id"), 0) AS m FROM "{nome}"'
            ).fetchone()
            cur.execute(
                "SELECT setval(%s, GREATEST(%s, 1), %s)",
                (seq, maxrow["m"], maxrow["m"] > 0),
            )
    pg.commit()
    print("[sequences] OK")


def conferir(sq: sqlite3.Connection, pg: psycopg.Connection, tabelas: list[str]) -> bool:
    ok = True
    print("\n[conferência] origem -> destino")
    for nome in tabelas:
        n_src = sq.execute(f"SELECT COUNT(*) FROM {nome}").fetchone()[0]
        with pg.cursor() as cur:
            n_dst = cur.execute(f'SELECT COUNT(*) AS n FROM "{nome}"').fetchone()["n"]
        status = "OK" if n_src == n_dst else "DIVERGE"
        if n_src != n_dst:
            ok = False
        print(f"  {status:8s} {nome:32s} {n_src:>8} -> {n_dst:>8}")
    return ok


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="scripts/migrar_postgres.py")
    ap.add_argument("--db", default=None, help="SQLite de origem (default: server.db)")
    ap.add_argument("--pg-url", default=None, help="URL Postgres (default: DATABASE_URL)")
    ap.add_argument("--apply-schema", action="store_true", help="aplica postgres_schema.sql antes")
    ap.add_argument("--schema-file", default=str(PROJECT / "scripts" / "postgres_schema.sql"))
    ap.add_argument("--crawler-db", default=None, help="SQLite do scraper (default: crawler.db)")
    ap.add_argument("--no-crawler", action="store_true", help="não migra o crawler.db")
    args = ap.parse_args(argv)

    sqlite_path = Path(args.db) if args.db else Path(SYSTEM_DB)
    pg_url = args.pg_url or os.getenv("DATABASE_URL", "")
    if not pg_url:
        print("ERRO: informe --pg-url ou defina DATABASE_URL", file=sys.stderr)
        return 2

    crawler_path = Path(args.crawler_db) if args.crawler_db else Path(CATALOG_DB)

    print(f"[origem ] SQLite  : {sqlite_path}")
    print(f"[destino] Postgres: {pg_url}")

    if not sqlite_path.exists():
        print(f"ERRO: banco SQLite não existe: {sqlite_path}", file=sys.stderr)
        return 2

    sq = sqlite3.connect(sqlite_path)
    tabelas = listar_tabelas(sq)
    print(f"[info] {len(tabelas)} tabelas a copiar")

    ok = True
    try:
        with psycopg.connect(pg_dsn(pg_url), row_factory=dict_row) as pg:
            if args.apply_schema:
                aplicar_schema_runner(pg_url, Path(args.schema_file))

            if not args.no_crawler and crawler_path.exists():
                aplicar_schema_scraper(pg)

            # desativa FKs durante o import (evita violação por ordem de carga)
            pg.autocommit = True
            with pg.cursor() as cur:
                cur.execute("SET session_replication_role = replica")
            pg.autocommit = False

            for nome in tabelas:
                print(f"[import] {nome} ...")
                n = copiar_tabela(sq, pg, nome)
                print(f"  {nome}: {n} linhas")

            # reativa FKs e valida
            pg.autocommit = True
            with pg.cursor() as cur:
                cur.execute("SET session_replication_role = DEFAULT")
            pg.autocommit = False

            ajustar_sequences(pg, tabelas)
            ok = conferir(sq, pg, tabelas)

            if not args.no_crawler and crawler_path.exists():
                sq_crawler = sqlite3.connect(crawler_path)
                try:
                    tabelas_crawler = listar_tabelas(sq_crawler)
                    print(f"[crawler] {len(tabelas_crawler)} tabelas a copiar")
                    pg.commit()
                    pg.autocommit = True
                    with pg.cursor() as cur:
                        cur.execute("SET session_replication_role = replica")
                    pg.autocommit = False
                    for nome in tabelas_crawler:
                        print(f"[import] crawler/{nome} ...")
                        n = copiar_tabela(sq_crawler, pg, nome)
                        print(f"  {nome}: {n} linhas")
                    pg.commit()
                    pg.autocommit = True
                    with pg.cursor() as cur:
                        cur.execute("SET session_replication_role = DEFAULT")
                    pg.autocommit = False
                    ajustar_sequences(pg, tabelas_crawler)
                    ok_crawler = conferir(sq_crawler, pg, tabelas_crawler)
                    ok = ok and ok_crawler
                finally:
                    sq_crawler.close()
    finally:
        sq.close()

    if ok:
        print("\nMigração concluída com sucesso.")
        return 0
    print("\nATENÇÃO: divergências nas contagens (ver acima).", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())