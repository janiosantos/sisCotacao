"""Runner de migrações versionadas para o SQLite do catálogo/cotações.

O `db.init_db()` deixa de executar um SCHEMA estático e passa a aplicar as
versões pendentes da pasta `versions/`. Cada arquivo `NNNN_desc.sql|py` é uma
migração atômica registrada em `schema_migrations`; `PRAGMA user_version`
espelha a maior versão aplicada.

CLI:
    python -m catalog_server.migrations status
    python -m catalog_server.migrations apply [--up-to N]
    python -m catalog_server.migrations rollback [--to N]
    python -m catalog_server.migrations check
    python -m catalog_server.migrations backup

Formato `.sql` : script SQL idempotente (CREATE TABLE/INDEX IF NOT EXISTS).
Formato `.py`  : módulo com o contrato:
    VERSION: int
    NAME: str
    guard(conn) -> bool        # True quando o banco JÁ está no estado-alvo
    forward(conn) -> None      # aplica (pode abrir BEGIN/COMMIT próprios)
    backward(conn) -> None     # opcional; desfaz
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import sqlite3
import sys
import threading
from datetime import datetime
from pathlib import Path

from catalog_server.config import SYSTEM_DB

MIGRATIONS_DIR = Path(__file__).resolve().parent / "versions"

# Processo deste servidor já levou o banco às versões finais (evita re-scan do
# disco e re-abertura da migração a cada conexão `system_conn()`).
_MIGRATED: set[Path] = set()
_MIGRATED_LOCK = threading.Lock()


class MigrationError(Exception):
    pass


class Migration:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.kind = "sql" if path.suffix == ".sql" else "py"
        try:
            self.version = int(path.name.split("_", 1)[0])
        except (ValueError, IndexError):
            raise MigrationError(f"migração sem versão numérica no nome: {path.name}")
        self.name = path.stem
        self._mod = None
        self._script = None

    @property
    def checksum(self) -> str:
        return hashlib.sha256(self.path.read_bytes()).hexdigest()

    @property
    def sql_script(self) -> str:
        if self._script is None:
            self._script = self.path.read_text(encoding="utf-8")
        return self._script

    @property
    def module(self):
        if self._mod is None:
            if self.kind != "py":
                raise MigrationError(f"{self.path.name} não é migração Python")
            spec = importlib.util.spec_from_file_location(
                f"_migration_{self.version}", self.path
            )
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)  # type: ignore[union-attr]
            self._mod = mod
        return self._mod

    def guard(self, conn: sqlite3.Connection) -> bool:
        if self.kind == "py":
            g = getattr(self.module, "guard", None)
            if g is not None:
                return bool(g(conn))
        return False

    def forward(self, conn: sqlite3.Connection) -> None:
        if self.kind == "sql":
            conn.executescript(self.sql_script)
        else:
            f = getattr(self.module, "forward", None)
            if f is None:
                raise MigrationError(f"{self.path.name} não define forward(conn)")
            f(conn)

    def backward(self, conn: sqlite3.Connection) -> None:
        if self.kind != "py":
            raise MigrationError(f"{self.path.name} (.sql) não tem rollback")
        b = getattr(self.module, "backward", None)
        if b is None:
            raise MigrationError(f"{self.path.name} não define backward(conn)")
        b(conn)


def load_migrations() -> list[Migration]:
    files = sorted(
        p
        for p in MIGRATIONS_DIR.iterdir()
        if p.suffix in (".sql", ".py") and p.name[0].isdigit()
    )
    migs = [Migration(p) for p in files]
    versions = [m.version for m in migs]
    if len(versions) != len(set(versions)):
        raise MigrationError("versões duplicadas em migrations/versions/")
    return migs


def _connect(db_path: str | Path) -> sqlite3.Connection:
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path, timeout=30)
    conn.isolation_level = None  # autocommit: cada migração controla a transação
    conn.execute("PRAGMA busy_timeout = 10000")
    try:
        conn.execute("PRAGMA journal_mode = WAL")
    except sqlite3.OperationalError:
        pass  # WAL indisponível (ex.: memória)
    return conn


def _ensure_tracking(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version      INTEGER PRIMARY KEY,
            name         TEXT NOT NULL,
            checksum     TEXT NOT NULL,
            applied_at   TEXT NOT NULL DEFAULT (datetime('now'))
        );
        """
    )


def applied_versions(conn: sqlite3.Connection) -> dict[int, str]:
    _ensure_tracking(conn)
    rows = conn.execute("SELECT version, checksum FROM schema_migrations").fetchall()
    return {v: c for v, c in rows}


def _record(conn: sqlite3.Connection, mig: Migration) -> None:
    conn.execute(
        "INSERT OR REPLACE INTO schema_migrations (version, name, checksum) VALUES (?,?,?)",
        (mig.version, mig.name, mig.checksum),
    )
    maxv = conn.execute("SELECT MAX(version) FROM schema_migrations").fetchone()[0] or 0
    conn.execute(f"PRAGMA user_version = {int(maxv)}")


def _backup(db_path: Path, version: int) -> Path:
    """Backup via API sqlite (arquivo p/ arquivo) antes de migrações .py."""
    db_path = Path(db_path)
    bak_dir = db_path.parent / "Backups"
    bak_dir.mkdir(parents=True, exist_ok=True)
    dest = bak_dir / f"pre_{version}_{datetime.now():%Y%m%d_%H%M%S}.db"
    src = sqlite3.connect(db_path)
    dst = sqlite3.connect(dest)
    try:
        src.backup(dst)
    finally:
        dst.close()
        src.close()
    return dest


def backup_db(db_path: Path) -> Path:
    """Backup explícito (CLI `backup`)."""
    conn = _connect(db_path)
    try:
        done = applied_versions(conn)
        uv = conn.execute("PRAGMA user_version").fetchone()[0]
    finally:
        conn.close()
    label = uv or max(done) if done else uv
    return _backup(db_path, label)


def apply(
    db_path: Path,
    up_to: int | None = None,
    backup_py: bool = True,
    _lock: bool = True,
) -> list[int]:
    """Aplica as migrações pendentes (<= up_to) e devolve as versões aplicadas.

    A versão é registrada em `schema_migrations` e `PRAGMA user_version` é
    atualizado. Migrações `.py` ganham backup automático antes de rodar (o
    rebuild de tabelas não é reversível por SQL puro).
    """
    db_path = Path(db_path)
    if _lock:
        with _MIGRATED_LOCK:
            return _apply_inner(db_path, up_to, backup_py)
    return _apply_inner(db_path, up_to, backup_py)


def _apply_inner(db_path: Path, up_to: int | None, backup_py: bool) -> list[int]:
    conn = _connect(db_path)
    try:
        done = applied_versions(conn)
        applied_here: list[int] = []
        for mig in load_migrations():
            if mig.version in done or (up_to is not None and mig.version > up_to):
                continue
            if mig.guard(conn):
                # banco já no estado-alvo: só registra (idempotência)
                _record(conn, mig)
                applied_here.append(mig.version)
                continue
            if mig.kind == "py" and backup_py:
                _backup(db_path, mig.version)
            mig.forward(conn)
            _record(conn, mig)
            applied_here.append(mig.version)
        return applied_here
    finally:
        conn.close()


def rollback(db_path: Path, to_version: int | None = None) -> list[int]:
    """Desfaz migrações `.py` na ordem inversa até `to_version` (exclusivo).

    Migrações `.sql` idempotentes não são desfeitas.
    """
    conn = _connect(db_path)
    try:
        done = applied_versions(conn)
        target = to_version if to_version is not None else 0
        reverted: list[int] = []
        for mig in sorted(load_migrations(), key=lambda m: -m.version):
            if mig.version <= target or mig.version not in done:
                continue
            mig.backward(conn)
            conn.execute("DELETE FROM schema_migrations WHERE version=?", (mig.version,))
            maxv = conn.execute("SELECT MAX(version) FROM schema_migrations").fetchone()[0] or 0
            conn.execute(f"PRAGMA user_version = {int(maxv)}")
            reverted.append(mig.version)
        return reverted
    finally:
        conn.close()


def check_db(db_path: Path) -> list[str]:
    conn = _connect(db_path)
    try:
        out = []
        integ = conn.execute("PRAGMA integrity_check").fetchone()[0]
        out.append(f"integrity_check: {integ}")
        fk = conn.execute("PRAGMA foreign_key_check").fetchall()
        out.append(f"foreign_key_check: {'OK' if not fk else fk}")
        uv = conn.execute("PRAGMA user_version").fetchone()[0]
        out.append(f"user_version: {uv}")
        maxv = conn.execute("SELECT COALESCE(MAX(version),0) FROM schema_migrations").fetchone()[0]
        out.append(f"schema_migrations max: {maxv}")
        return out
    finally:
        conn.close()


def status(db_path: Path) -> str:
    conn = _connect(db_path)
    try:
        done = applied_versions(conn)
        lines = [f"{'VERS':>5} {'SITUAÇÃO':<10} {'MIGRAÇÃO':<38} CHECKSUM"]
        lines.append("-" * 90)
        for mig in load_migrations():
            if mig.version in done:
                ok = "ok" if done[mig.version] == mig.checksum else "checksum≠"
                lines.append(
                    f"{mig.version:>5} {'Aplicada':<10} {mig.name:<38} {ok}"
                )
            else:
                lines.append(f"{mig.version:>5} {'Pendente':<10} {mig.name:<38}")
        return "\n".join(lines)
    finally:
        conn.close()


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m catalog_server.migrations")
    ap.add_argument("--db", default=str(SYSTEM_DB), help="caminho do banco")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_status = sub.add_parser("status", help="lista as versões aplicadas/pendentes")
    p_apply = sub.add_parser("apply", help="aplica as migrações pendentes")
    p_apply.add_argument("--up-to", type=int, default=None)
    p_roll = sub.add_parser("rollback", help="desfaz versões (somente .py)")
    p_roll.add_argument("--to", type=int, default=None)
    sub.add_parser("check", help="integridade + FKs + versões")
    sub.add_parser("backup", help="backup do banco via API sqlite")

    args = ap.parse_args(argv)
    db_path = Path(args.db)

    if args.cmd == "status":
        print(status(db_path))
    elif args.cmd == "apply":
        done = apply(db_path, up_to=args.up_to)
        print(f"versões aplicadas: {done}")
        print(status(db_path))
    elif args.cmd == "rollback":
        reverted = rollback(db_path, to_version=args.to)
        print(f"versões desfeitas: {reverted}")
        print(status(db_path))
    elif args.cmd == "check":
        for line in check_db(db_path):
            print(line)
    elif args.cmd == "backup":
        print(f"backup: {backup_db(db_path)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
