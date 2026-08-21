"""Versionamento do sistema: liga a versão do deploy (``APP_VERSION``) à versão
do schema (migrações aplicadas) e expõe o estado de atualizações pendentes.

Leitura **sob demanda e somente-leitura**: não aplica migrações nem cria/altera
tabelas — apenas consulta ``schema_migrations`` e os arquivos de migração.

``apply_updates`` aplica migrações pendentes (filtradas por `riscos`) e registra
o evento na tabela ``sistema_atualizacoes`` (ver migrações 0061/0062), incluindo
as notas de cada manifesto de release (``releases/vX.Y.Z.json``): correções,
melhorias e recursos — alimentando o Histórico do Painel de Atualizações.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import psycopg
from psycopg.types.json import Json

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
        with psycopg.connect(_dsn(), connect_timeout=3) as conn:
            rows = conn.execute("SELECT version FROM schema_migrations").fetchall()
        return {int(r[0]) for r in rows}
    except Exception:
        return set()


def _schema_version() -> int:
    applied = _applied_versions()
    return max(applied) if applied else 0


# ---------------------------------------------------------------------------
# Manifestos de release (releases/vX.Y.Z.json)
# ---------------------------------------------------------------------------

def _releases_dir() -> Path:
    return Path(__file__).resolve().parent.parent / "releases"


def _versao_key(versao: str) -> tuple[int, ...]:
    partes = [p for p in versao.lstrip("v").split(".") if p.isdigit()]
    return tuple(int(p) for p in partes) or (0,)


def _publicadas() -> set[str]:
    """Versões de release já registradas no log (tolera tabela ausente)."""
    try:
        with psycopg.connect(_dsn(), connect_timeout=3) as conn:
            rows = conn.execute(
                "SELECT DISTINCT versao_release FROM sistema_atualizacoes"
                " WHERE versao_release IS NOT NULL"
            ).fetchall()
        return {r[0] for r in rows}
    except Exception:
        return set()


def listar_manifestos_pendentes() -> list[dict]:
    """Manifestos em `releases/` ainda não publicados (ordenados por versão)."""
    publicadas = _publicadas()
    out: list[dict] = []
    d = _releases_dir()
    if not d.is_dir():
        return out
    for f in sorted(d.glob("*.json")):
        try:
            m = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            continue
        if not isinstance(m, dict) or not m.get("versao"):
            continue
        if m["versao"] in publicadas:
            continue
        out.append(m)
    out.sort(key=lambda m: _versao_key(str(m.get("versao"))))
    return out


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


def _nivel_label(riscos: list[str] | None) -> str:
    if riscos is None:
        return "todos"
    if set(riscos) >= {"critica", "rotina", "melhoria"}:
        return "melhoria"
    if set(riscos) >= {"critica", "rotina"}:
        return "rotina"
    return ",".join(riscos)


def _registrar_log(
    *,
    nivel: str,
    versao_app: str,
    schema_antes: int,
    schema_depois: int,
    total_aplicadas: int,
    origem: str,
    usuario: str | None,
    detalhes: dict | None = None,
    erro: str | None = None,
    versao_release: str | None = None,
    componentes: list | None = None,
    correcoes: list | None = None,
    melhorias: list | None = None,
    recursos: list | None = None,
) -> None:
    """Grava o evento de atualização. Falhas de log são ignoradas."""
    try:
        with psycopg.connect(_dsn(), connect_timeout=3) as conn:
            conn.execute(
                """
                INSERT INTO sistema_atualizacoes
                    (nivel, versao_app, schema_antes, schema_depois,
                     total_aplicadas, detalhes, origem, usuario, erro,
                     versao_release, componentes, correcoes, melhorias, recursos)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    nivel,
                    versao_app,
                    schema_antes,
                    schema_depois,
                    total_aplicadas,
                    Json(detalhes) if detalhes is not None else None,
                    origem,
                    usuario,
                    erro,
                    versao_release,
                    Json(componentes) if componentes is not None else None,
                    Json(correcoes) if correcoes is not None else None,
                    Json(melhorias) if melhorias is not None else None,
                    Json(recursos) if recursos is not None else None,
                ),
            )
            conn.commit()
    except Exception:
        pass


def apply_updates(
    riscos: list[str] | None = None,
    origem: str = "deploy",
    usuario: str | None = None,
) -> dict:
    """Aplica migrações pendentes (filtradas por `riscos`) e registra o evento.

    Usado pelo deploy (origem="deploy") e pelo painel (origem="painel").
    """
    antes = _schema_version()
    nivel = _nivel_label(riscos)
    try:
        applied = apply(_dsn(), riscos=riscos)
        st = system_status()
        _registrar_log(
            nivel=nivel,
            versao_app=st["app_version"],
            schema_antes=antes,
            schema_depois=st["schema_version"],
            total_aplicadas=len(applied),
            origem=origem,
            usuario=usuario,
            detalhes={"aplicadas": applied},
        )
        # Publicação via deploy: registra um evento por manifesto pendente,
        # na sequência das versões — o Histórico mostra O QUE foi lançado.
        if origem == "deploy":
            for m in listar_manifestos_pendentes():
                _registrar_log(
                    nivel="release",
                    versao_app=st["app_version"],
                    schema_antes=antes,
                    schema_depois=st["schema_version"],
                    total_aplicadas=0,
                    origem="release",
                    usuario=usuario,
                    detalhes={"manifesto": m.get("versao")},
                    versao_release=m.get("versao"),
                    componentes=m.get("componentes"),
                    correcoes=m.get("correcoes"),
                    melhorias=m.get("melhorias"),
                    recursos=m.get("recursos"),
                )
        return st
    except Exception as e:
        erro = str(e)
        try:
            st = system_status()
            depois, versao = st["schema_version"], st["app_version"]
        except Exception:
            depois, versao = antes, "desconhecido"
        _registrar_log(
            nivel=nivel,
            versao_app=versao,
            schema_antes=antes,
            schema_depois=depois,
            total_aplicadas=0,
            origem=origem,
            usuario=usuario,
            erro=erro,
        )
        raise


def listar_log(limite: int = 50) -> list[dict]:
    """Retorna os últimos eventos de atualização (tolerante a tabela ausente)."""
    try:
        with psycopg.connect(_dsn(), connect_timeout=3) as conn:
            rows = conn.execute(
                """
                SELECT id, executado_em, nivel, versao_app, schema_antes,
                       schema_depois, total_aplicadas, origem, usuario, erro,
                       versao_release, componentes, correcoes, melhorias, recursos
                FROM sistema_atualizacoes
                ORDER BY executado_em DESC, id DESC
                LIMIT %s
                """,
                (limite,),
            ).fetchall()
        cols = [
            "id",
            "executado_em",
            "nivel",
            "versao_app",
            "schema_antes",
            "schema_depois",
            "total_aplicadas",
            "origem",
            "usuario",
            "erro",
            "versao_release",
            "componentes",
            "correcoes",
            "melhorias",
            "recursos",
        ]
        return [dict(zip(cols, r)) for r in rows]
    except Exception:
        return []


_RISCO_CLI = {
    "critica": ["critica"],
    "rotina": ["critica", "rotina"],
    "melhoria": ["critica", "rotina", "melhoria"],
    "todos": None,
}


def _main() -> int:
    p = argparse.ArgumentParser(description="Aplica migrações e registra o log.")
    p.add_argument("command", nargs="?", choices=["apply"], default="apply")
    p.add_argument("--origem", default="deploy")
    p.add_argument(
        "--risco", default="todos", choices=["critica", "rotina", "melhoria", "todos"]
    )
    p.add_argument("--usuario", default=None)
    args = p.parse_args()
    try:
        st = apply_updates(
            riscos=_RISCO_CLI[args.risco], origem=args.origem, usuario=args.usuario
        )
        print(json.dumps(st))
        return 0
    except Exception as e:  # noqa: BLE001
        print(json.dumps({"ok": False, "error": str(e)}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(_main())
