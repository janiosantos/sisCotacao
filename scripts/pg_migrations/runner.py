"""Runner de migrações versionadas para o PostgreSQL (banco único do ERP).

Estratégia de versões:
- A migração `0052_baseline_postgres` (versão 52) aplica
  `scripts/postgres_schema.sql` — o schema atual do sistema. Se o banco já
  possui o schema, o `guard` reconhece e apenas registra a versão (idempotente).
- Mudanças futuras entram como `NNNN_nome.sql|py` em `versions/` (numeração
  0053+), aplicadas incrementalmente sobre o baseline.
- Cada versão aplicada fica registrada na tabela `schema_migrations`.

CLI:
    python -m scripts.pg_migrations status [--url URL]
    python -m scripts.pg_migrations apply [--url URL] [--up-to N]
    python -m scripts.pg_migrations check [--url URL]

Formato `.sql` : script SQL idempotente (CREATE TABLE/INDEX IF NOT EXISTS).
Formato `.py`  : módulo com o contrato:
    VERSION: int
    NAME: str
    RISCO: str                 # 'critica' | 'melhoria' | 'rotina' | 'n/c' (controle de update)
    guard(conn) -> bool        # True quando o banco JÁ está no estado-alvo
    forward(conn) -> None      # aplica (pode abrir BEGIN/COMMIT próprios)
    backward(conn) -> None     # opcional; desfaz
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import os
import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent.parent

MIGRATIONS_DIR = Path(__file__).resolve().parent / "versions"

# Chave fixa do advisory lock que serializa o `apply` entre processos.
ADVISORY_LOCK_KEY = 723901140

# Arquivo SQL do baseline (schema completo do sistema).
SCHEMA_FILE = PROJECT / "scripts" / "postgres_schema.sql"


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
                f"_pg_migration_{self.version}", self.path
            )
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)  # type: ignore[union-attr]
            self._mod = mod
        return self._mod

    @property
    def risco(self) -> str:
        """Classificação de risco da migração (controle de update).

        'critica'   — muda estrutura central, recria tabelas ou altera dados em massa.
        'melhoria'  — nova funcionalidade aditiva / não-quebrante.
        'rotina'    — seed idempotente / ajuste pequeno de baixo risco.
        'n/c'       — não classificada (valor padrão quando ausente).
        """
        if self.kind == "py":
            r = getattr(self.module, "RISCO", None)
            if r:
                return str(r).strip().lower()
        return "n/c"

    def guard(self, conn) -> bool:
        if self.kind == "py":
            g = getattr(self.module, "guard", None)
            if g is not None:
                return bool(g(conn))
        return False

    def forward(self, conn) -> None:
        if self.kind == "sql":
            conn.execute(self.sql_script)
            conn.commit()
        else:
            f = getattr(self.module, "forward", None)
            if f is None:
                raise MigrationError(f"{self.path.name} não define forward(conn)")
            f(conn)

    def backward(self, conn) -> None:
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
        raise MigrationError("versões duplicadas em scripts/pg_migrations/versions/")
    return migs


def _dsn(url: str) -> str:
    if url.startswith("postgresql+psycopg://"):
        return url.replace("postgresql+psycopg://", "postgresql://", 1)
    return url


def _connect(url: str):
    import psycopg

    return psycopg.connect(_dsn(url))


def _ensure_tracking(conn) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version      INTEGER PRIMARY KEY,
            name         TEXT NOT NULL,
            checksum     TEXT NOT NULL,
            risco        TEXT NOT NULL DEFAULT 'n/c',
            applied_at   TEXT NOT NULL DEFAULT (to_char(now(),'YYYY-MM-DD HH24:MI:SS'))
        );
        """
    )
    # Tabelas já existentes (em produção) ganham a coluna de risco sem perda de dados.
    conn.execute(
        "ALTER TABLE schema_migrations ADD COLUMN IF NOT EXISTS risco TEXT NOT NULL DEFAULT 'n/c'"
    )
    conn.commit()


def applied_versions(conn) -> dict[int, str]:
    _ensure_tracking(conn)
    rows = conn.execute("SELECT version, checksum FROM schema_migrations").fetchall()
    return {v: c for v, c in rows}


def _record(conn, mig: Migration) -> None:
    conn.execute(
        "INSERT INTO schema_migrations (version, name, checksum, risco) VALUES (%s, %s, %s, %s)"
        " ON CONFLICT (version) DO UPDATE SET name = EXCLUDED.name,"
        " checksum = EXCLUDED.checksum, risco = EXCLUDED.risco",
        (mig.version, mig.name, mig.checksum, mig.risco),
    )
    conn.commit()


def apply(
    url: str,
    up_to: int | None = None,
    riscos: list[str] | None = None,
) -> list[int]:
    """Aplica as migrações pendentes (<= up_to) e devolve as versões aplicadas.

    Idempotente: versões já registradas são puladas; migrações `.py` com
    `guard` True (banco já no estado-alvo) são apenas registradas.

    Se `riscos` for informado, só aplica migrações cujo `risco` esteja nessa
    lista (controle de atualização por criticidade).
    """
    conn = _connect(url)
    try:
        # Lock de sessão do Postgres: serializa execuções concorrentes (dois
        # processos/containers subindo juntos não aplicam a mesma migração
        # duas vezes). Liberado no finally / ao fechar a conexão.
        conn.execute("SELECT pg_advisory_lock(%s)", (ADVISORY_LOCK_KEY,))
        conn.commit()
        done = applied_versions(conn)
        applied_here: list[int] = []
        for mig in load_migrations():
            if mig.version in done or (up_to is not None and mig.version > up_to):
                continue
            if riscos is not None and mig.risco not in riscos:
                continue
            try:
                already = mig.guard(conn)
            except Exception:
                # Guard falhou (ex.: tabela ainda não existe no banco). Trata
                # como "banco ainda não está no estado-alvo" e tenta o forward.
                already = False
                try:
                    conn.rollback()
                except Exception:
                    pass
            if already:
                _record(conn, mig)
                applied_here.append(mig.version)
                continue
            try:
                conn.commit()  # encerra transação aberta pelo guard (INTRANS)
            except Exception:
                pass
            mig.forward(conn)
            _record(conn, mig)
            applied_here.append(mig.version)
        return applied_here
    finally:
        try:
            conn.execute("SELECT pg_advisory_unlock(%s)", (ADVISORY_LOCK_KEY,))
            conn.commit()
        except Exception:
            pass
        conn.close()


def rollback(url: str, to_version: int | None = None) -> list[int]:
    """Desfaz migrações `.py` na ordem inversa até `to_version` (exclusivo)."""
    conn = _connect(url)
    try:
        done = applied_versions(conn)
        target = to_version if to_version is not None else 0
        reverted: list[int] = []
        for mig in sorted(load_migrations(), key=lambda m: -m.version):
            if mig.version <= target or mig.version not in done:
                continue
            mig.backward(conn)
            conn.execute("DELETE FROM schema_migrations WHERE version = %s", (mig.version,))
            conn.commit()
            reverted.append(mig.version)
        return reverted
    finally:
        conn.close()


def plan_pending(url: str) -> str:
    """Lista as migrações pendentes (serão aplicadas no próximo `apply`)."""
    conn = _connect(url)
    try:
        done = applied_versions(conn)
        lines = ["Migrações pendentes (serão aplicadas no próximo apply):"]
        any_pending = False
        for mig in load_migrations():
            if mig.version in done:
                continue
            any_pending = True
            lines.append(f"  -> {mig.version:>5}  [{mig.risco:<8}] {mig.name}")
        if not any_pending:
            lines.append("  (nenhuma)")
        return "\n".join(lines)
    finally:
        conn.close()


def check_db(url: str) -> list[str]:
    conn = _connect(url)
    try:
        out = []
        row = conn.execute("SELECT 1").fetchone()
        out.append(f"conexão: {'OK' if row else 'falhou'}")
        done = applied_versions(conn)
        maxv = max(done) if done else 0
        out.append(f"schema_migrations max: {maxv}")
        out.append(f"registradas: {len(done)}")
        pending = [m for m in load_migrations() if m.version not in done]
        out.append(f"pendentes: {len(pending)}")
        return out
    finally:
        conn.close()


def status(url: str) -> str:
    conn = _connect(url)
    try:
        done = applied_versions(conn)
        lines = [f"{'VERS':>5} {'SITUAÇÃO':<10} {'RISCO':<9} {'MIGRAÇÃO':<38} CHECKSUM"]
        lines.append("-" * 96)
        for mig in load_migrations():
            r = mig.risco
            if mig.version in done:
                ok = "ok" if done[mig.version] == mig.checksum else "checksum≠"
                lines.append(f"{mig.version:>5} {'Aplicada':<10} {r:<9} {mig.name:<38} {ok}")
            else:
                lines.append(f"{mig.version:>5} {'Pendente':<10} {r:<9} {mig.name:<38}")
        return "\n".join(lines)
    finally:
        conn.close()


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m scripts.pg_migrations")
    ap.add_argument("--url", default=os.getenv("DATABASE_URL", ""), help="URL do Postgres")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_status = sub.add_parser("status", help="lista as versões aplicadas/pendentes")
    p_apply = sub.add_parser("apply", help="aplica as migrações pendentes")
    p_apply.add_argument("--up-to", type=int, default=None)
    p_roll = sub.add_parser("rollback", help="desfaz versões (somente .py)")
    p_roll.add_argument("--to", type=int, default=None)
    sub.add_parser("plan", help="lista migrações pendentes (controle de update)")
    sub.add_parser("check", help="conexão + schema_migrations + pendentes")

    args = ap.parse_args(argv)
    if not args.url:
        print("ERRO: informe --url ou defina DATABASE_URL", file=sys.stderr)
        return 2

    if args.cmd == "status":
        print(status(args.url))
    elif args.cmd == "apply":
        done = apply(args.url, up_to=args.up_to)
        print(f"versões aplicadas: {done}")
        print(status(args.url))
    elif args.cmd == "rollback":
        reverted = rollback(args.url, to_version=args.to)
        print(f"versões desfeitas: {reverted}")
        print(status(args.url))
    elif args.cmd == "plan":
        print(plan_pending(args.url))
    elif args.cmd == "check":
        for line in check_db(args.url):
            print(line)
    return 0


if __name__ == "__main__":
    sys.exit(main())
