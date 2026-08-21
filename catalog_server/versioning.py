"""Versionamento do sistema: liga a versão do deploy (``APP_VERSION``) à versão
do schema (migrações aplicadas) e expõe o estado de atualizações pendentes.

Leitura **sob demanda e somente-leitura**: não aplica migrações nem cria/altera
tabelas — apenas consulta ``schema_migrations`` e os arquivos de migração.
"""
from __future__ import annotations

import os

import psycopg

from catalog_server import config
from scripts.pg_migrations.runner import apply, load_migrations

# Ordem canônica de classificação de risco (para o resumo do endpoint).
RISCOS = ("critica", "melhoria", "rotina", "n/c")


def _dsn() -> str:
    url = config.DATABASE_URL or ""
    if url.startswith("postgresql+psycopg://"):
        url = url.replace("postgresql+psycopg://", "postgresql://", 1)
    return url


def _applied_versions() -> set[int]:
    """Versões registradas em ``schema_migrations`` (read-only; tolera tabela ausente)."""
    try:
        with psycopg.connect(_dsn()) as conn:
            rows = conn.execute("SELECT version FROM schema_migrations").fetchall()
        return {int(r[0]) for r in rows}
    except Exception:
        return set()


def system_status() -> dict:
    app_version = os.getenv("APP_VERSION") or "dev"
    applied = _applied_versions()
    migs = load_migrations()
    applied_set = set(applied)
    schema_version = max(applied) if applied else 0
    pending = [
        {"version": m.version, "name": m.name, "risco": m.risco}
        for m in migs
        if m.version not in applied_set
    ]
    por_risco: dict[str, int] = {r: 0 for r in RISCOS}
    for p in pending:
        por_risco[p["risco"]] = por_risco.get(p["risco"], 0) + 1
    return {
        "app_version": app_version,
        "schema_version": schema_version,
        "schema_max": max((m.version for m in migs), default=0),
        "applied": len(applied),
        "total_migrations": len(migs),
        "pending": pending,
        "pending_por_risco": por_risco,
        "atualizado": len(pending) == 0,
    }


def apply_updates(riscos: list[str] | None = None) -> dict:
    """Aplica migrações pendentes (filtradas por `riscos`) e devolve o novo estado.

    Usado pelo painel "Atualizações" para aplicar mudanças de forma on-demand,
    separado do apply automático na subida do container.
    """
    apply(_dsn(), riscos=riscos)
    st = system_status()
    return st
