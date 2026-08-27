"""Camada de compatibilidade SQLite->PostgreSQL.

Quando `DATABASE_URL` está configurada, `db.system_conn()` devolve uma
`PgConnection` (este módulo) que imita o contrato de API do `sqlite3` usado
pelos repositórios:

- `execute(sql, params)` -> cursor com `.fetchone()`, `.fetchall()`,
  `.rowcount`, `.lastrowid` e iteração.
- Linhas aceitam tanto `row["col"]` quanto `row[0]`, `dict(row)`, `len(row)`,
  `row.keys()`, `.items()` e `.values()`.
- `commit()`/`close()` e contexto (`with`).
- `PRAGMA foreign_keys = ON` é ignorado (Postgres sempre valida FKs).

O SQL dos repositórios é escrito para SQLite; `translate_sql()` converte os
idiomas conhecidos para o dialeto Postgres antes de executar:

- `?`          -> `%s`
- `datetime('now')` -> `to_char(now(),'YYYY-MM-DD HH24:MI:SS')`
- `date('now'[, '+N days'])` -> `to_char(now() [...],'YYYY-MM-DD')`
- `date(col)`  -> `substr(col, 1, 10)`
- `INSERT OR IGNORE INTO`  -> `INSERT INTO ... ON CONFLICT DO NOTHING`
- `INSERT OR REPLACE INTO` -> `INSERT INTO ... ON CONFLICT DO NOTHING`
- `LIKE ? COLLATE NOCASE`/`LIKE ?` -> `ILIKE ?`
- `expr COLLATE NOCASE` (ORDER BY) -> `LOWER(expr)`
- `GROUP_CONCAT(x, 'sep')` -> `string_agg(x, 'sep')`
- `last_insert_rowid()` -> `lastval()`
"""
from __future__ import annotations

import re

import sqlalchemy

# ---------------------------------------------------------------------------
# Tradução SQL
# ---------------------------------------------------------------------------

# tokens para mascarar strings ('...') e literais conhecidos durante as
# substituições (evita regex casando dentro de literais).
_MASK = re.compile(r"__PGSQL__(\d+)__")

_NOW_FORMAT = "'YYYY-MM-DD HH24:MI:SS'"
_DATE_FORMAT = "'YYYY-MM-DD'"

# date('now', '-30 days') / date('now', '+N unit')
_MOD = re.compile(
    r"date\(\s*'now'\s*(?:,\s*'([+-]?\d+)\s+(days|months|years)'\s*)?\)",
    re.IGNORECASE,
)


def _lit_repl(m: re.Match) -> str:
    n = int(m.group(1) or "0")
    unit = m.group(2) or "days"
    if n == 0:
        return f"to_char(now(),{_DATE_FORMAT})"
    sign = "+" if n > 0 else "-"
    return f"to_char(now() {sign} interval '{abs(n)} {unit}',{_DATE_FORMAT})"


def translate_sql(sql: str) -> str:
    """Converte um statement SQLite para o dialeto Postgres (sem params)."""
    sql = sql.replace("datetime('now')", f"to_char(now(),{_NOW_FORMAT})")
    sql = _MOD.sub(_lit_repl, sql)
    # date(col_qualquer) -> substr(col, 1, 10)
    sql = re.sub(r"\bdate\((\w+(?:\.\w+)?)\)", r"substr(\1, 1, 10)", sql, flags=re.IGNORECASE)

    # máscara de literais de string para as substituições seguintes
    strings: list[str] = []
    parts: list[str] = []
    buf: list[str] = []
    s_buf: list[str] = []
    in_str = False
    i = 0
    while i < len(sql):
        ch = sql[i]
        if in_str:
            s_buf.append(ch)
            if ch == "'":
                if i + 1 < len(sql) and sql[i + 1] == "'":
                    s_buf.append("'")
                    i += 1
                else:
                    in_str = False
                    parts.append(f"__PGSQL__{len(strings)}__")
                    strings.append("".join(s_buf))
                    s_buf = []
        elif ch == "'":
            parts.append("".join(buf))
            buf = []
            in_str = True
            s_buf.append(ch)
        else:
            buf.append(ch)
        i += 1
    parts.append("".join(buf))
    masked = "".join(parts)

    upsert = None
    if re.match(r"INSERT\s+OR\s+IGNORE\s+INTO", masked, re.IGNORECASE):
        masked = re.sub(r"INSERT\s+OR\s+IGNORE\s+INTO", "INSERT INTO", masked, count=1, flags=re.IGNORECASE)
        upsert = "ON CONFLICT DO NOTHING"
    elif re.match(r"INSERT\s+OR\s+REPLACE\s+INTO", masked, re.IGNORECASE):
        masked = re.sub(r"INSERT\s+OR\s+REPLACE\s+INTO", "INSERT INTO", masked, count=1, flags=re.IGNORECASE)
        upsert = "ON CONFLICT DO NOTHING"

    # FTS removido (migração 0091): a busca usa ILIKE + pg_trgm sobre colunas.

    # LIKE case-insensitive (LIKE do SQLite é insensível por padrão)
    masked = re.sub(r"LIKE\s+\?\s+COLLATE\s+NOCASE", "ILIKE ?", masked, flags=re.IGNORECASE)
    masked = re.sub(r"\bLIKE\s+\?", "ILIKE ?", masked, flags=re.IGNORECASE)
    # expr COLLATE NOCASE -> LOWER(expr) (ordenação insensível a caixa)
    masked = re.sub(r"(\w+(?:\.\w+)?)\s+COLLATE\s+NOCASE", r"LOWER(\1)", masked, flags=re.IGNORECASE)
    masked = re.sub(r"\bCOLLATE\s+NOCASE\b", "", masked, flags=re.IGNORECASE)
    masked = re.sub(r"GROUP_CONCAT\(", "string_agg(", masked, flags=re.IGNORECASE)
    masked = masked.replace("last_insert_rowid()", "lastval()")

    if upsert:
        masked = masked.rstrip().rstrip(";") + f" {upsert};"

    # placeholders ? -> %s
    masked = masked.replace("?", "%s")

    # restaura strings (escapando % literal, que psycopg interpretaria como
    # placeholder — ex.: LIKE '%cor%')
    def _restore(m: re.Match) -> str:
        return strings[int(m.group(1))].replace("%", "%%")

    return _MASK.sub(_restore, masked)


# ---------------------------------------------------------------------------
# Row / Cursor / Connection
# ---------------------------------------------------------------------------


class PgRow:
    """Linha com acesso por nome ou por posição (como `sqlite3.Row`)."""

    __slots__ = ("_cols", "_values")

    def __init__(self, cols: list[str], values: tuple) -> None:
        self._cols = cols
        self._values = tuple(values)

    def _index(self, key) -> int:
        if isinstance(key, int):
            return key if key >= 0 else len(self._cols) + key
        if isinstance(key, str):
            for i, c in enumerate(self._cols):
                if c == key:
                    return i
            raise KeyError(key)
        raise TypeError(f"índice de linha deve ser int ou str, obtido: {type(key).__name__}")

    def __getitem__(self, key):
        return self._values[self._index(key)]

    def __iter__(self):
        return iter(self._values)

    def __len__(self) -> int:
        return len(self._cols)

    def __contains__(self, key) -> bool:
        return key in self._cols

    def keys(self):
        return list(self._cols)

    def items(self):
        return list(zip(self._cols, self._values))

    def values(self):
        return list(self._values)

    def as_dict(self) -> dict:
        return dict(self.items())

    def __repr__(self) -> str:
        return f"<PgRow {dict(self.items())}>"


class PgCursor:
    """Cursor compatível com o `sqlite3.Cursor` usado nos repositórios."""

    def __init__(self, conn: "PgConnection", sql: str, params) -> None:
        self._conn = conn
        self._description: list | None = None
        self.rowcount = -1
        self.lastrowid: int | None = None
        self._rows: list[PgRow] = []
        self._pos = 0
        self._execute(sql, params)

    def _execute(self, sql: str, params) -> None:
        translated = translate_sql(sql)
        raw = self._conn._conn.execute(translated, params or ())
        if raw.description is not None:
            self._description = [d[0] for d in raw.description]
            rows = raw.fetchall()
            self._rows = [PgRow(self._description, r) for r in rows]
        else:
            self.rowcount = raw.rowcount
        if re.match(r"\s*INSERT\b", sql, re.IGNORECASE) and not re.search(r"\bRETURNING\b", sql, re.IGNORECASE):
            self._set_lastrowid()

    def _set_lastrowid(self) -> None:
        # SAVEPOINT: se a tabela não tiver sequence, lastval() falha e abortaria
        # a transação; o rollback para o savepoint a mantém utilizável.
        try:
            self._conn._conn.execute("SAVEPOINT pgsql_lastrowid")
            row = self._conn._conn.execute("SELECT lastval()").fetchone()
            self.lastrowid = int(row[0]) if row else None
            self._conn._conn.execute("RELEASE SAVEPOINT pgsql_lastrowid")
        except Exception:  # noqa: BLE001 (tabela sem sequence)
            try:
                self._conn._conn.execute("ROLLBACK TO SAVEPOINT pgsql_lastrowid")
                self._conn._conn.execute("RELEASE SAVEPOINT pgsql_lastrowid")
            except Exception:  # noqa: BLE001
                pass
            self.lastrowid = None

    def fetchone(self) -> PgRow | None:
        if self._pos >= len(self._rows):
            return None
        row = self._rows[self._pos]
        self._pos += 1
        return row

    def fetchall(self) -> list[PgRow]:
        out = self._rows[self._pos :]
        self._pos = len(self._rows)
        return out

    def fetchmany(self, size: int = 1) -> list[PgRow]:
        out = self._rows[self._pos : self._pos + size]
        self._pos += len(out)
        return out

    def __iter__(self):
        return self

    def __next__(self) -> PgRow:
        row = self.fetchone()
        if row is None:
            raise StopIteration
        return row


class PgConnection:
    """Conexão compatível com o `sqlite3.Connection` dos repositórios."""

    def __init__(self, url: str) -> None:
        self._url = url
        # connect_timeout curto: com o banco fora do ar a requisição falha
        # rápido (503 db_indisponivel) em vez de pendurar o worker.
        self._engine = sqlalchemy.create_engine(
            url, pool_pre_ping=True, connect_args={"connect_timeout": 3}
        )
        self._conn = self._engine.raw_connection()
        self.is_pg = True

    def execute(self, sql: str, params=None) -> PgCursor:
        return PgCursor(self, sql, params)

    def executemany(self, sql: str, seq_of_params) -> PgCursor:
        last: PgCursor | None = None
        for params in seq_of_params:
            last = PgCursor(self, sql, params)
        return last if last is not None else PgCursor(self, "SELECT 1", None)

    def commit(self) -> None:
        self._conn.commit()

    def rollback(self) -> None:
        self._conn.rollback()

    def close(self) -> None:
        try:
            self._conn.close()
        finally:
            self._engine.dispose()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        if exc_type is None:
            self.commit()
        self.close()

    def __getattr__(self, name):
        # PRAGMA é executado via execute(); outros atributos (row_factory etc.)
        # são ignorados para manter a compatibilidade com o sqlite3.
        raise AttributeError(name)


def connect(url: str) -> PgConnection:
    return PgConnection(url)


__all__ = ["connect", "PgConnection", "PgRow", "translate_sql"]
