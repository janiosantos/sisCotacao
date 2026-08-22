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
from migrations.runner import apply, load_migrations

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
    # Container: /app/catalog_server/.. = /app/releases (montagem do compose).
    # Repo local: backend/catalog_server/../.. = raiz/releases.
    aqui = Path(__file__).resolve().parent.parent / "releases"
    if aqui.is_dir():
        return aqui
    return Path(__file__).resolve().parent.parent.parent / "releases"


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
        {
            "version": m.version,
            "name": m.name,
            "risco": m.risco,
            "mudanca": m.mudanca,
        }
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
    sem_docs: bool = False,
) -> dict:
    """Aplica migrações pendentes (filtradas por `riscos`) e registra o evento.

    Usado pelo deploy (origem="deploy") e pelo painel (origem="painel").
    O registro de RELEASES publicadas é feito por `registrar_publicacao()`,
    desacoplado das migrações — assim deploys só-frontend também geram log.
    """
    antes = _schema_version()
    nivel = _nivel_label(riscos)
    try:
        applied = apply(_dsn(), riscos=riscos, sem_docs=sem_docs)
        st = system_status()
        # Documentação das migrações aplicadas (o_que/porque/novidades).
        docs: dict[int, dict] = {}
        if applied:
            docs = {
                m.version: {
                    "nome": m.name,
                    "risco": m.risco,
                    **(m.mudanca or {}),
                }
                for m in load_migrations()
                if m.version in applied
            }
        _registrar_log(
            nivel=nivel,
            versao_app=st["app_version"],
            schema_antes=antes,
            schema_depois=st["schema_version"],
            total_aplicadas=len(applied),
            origem=origem,
            usuario=usuario,
            detalhes={
                "aplicadas": applied,
                "migracoes": [docs[v] for v in sorted(docs)] if docs else [],
            },
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


def registrar_publicacao(
    componentes_deploy: list[str],
    usuario: str | None = None,
) -> list[str]:
    """Registra no Histórico os manifestos cobertos pelo escopo publicado.

    Regra do subconjunto: um manifesto fecha quando TODOS os componentes que
    ele declara estão contidos nos `componentes_deploy` (ou quando o deploy é
    'todos'). Publicação parcial de um manifesto misto não o fecha.
    """
    versao_app = os.getenv("APP_VERSION") or "dev"
    agora = _schema_version()
    escopo = set(componentes_deploy)
    publicadas: list[str] = []
    for m in listar_manifestos_pendentes():
        comps = set(m.get("componentes") or [])
        if comps and not comps <= escopo:
            continue
        _registrar_log(
            nivel="release",
            versao_app=versao_app,
            schema_antes=agora,
            schema_depois=agora,
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
        publicadas.append(str(m.get("versao")))
    return publicadas


def listar_log(limite: int = 50) -> list[dict]:
    """Retorna os últimos eventos de atualização (tolerante a tabela ausente)."""
    try:
        with psycopg.connect(_dsn(), connect_timeout=3) as conn:
            rows = conn.execute(
                """
                SELECT id, executado_em, nivel, versao_app, schema_antes,
                       schema_depois, total_aplicadas, origem, usuario, erro,
                       versao_release, componentes, correcoes, melhorias,
                       recursos, detalhes
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
            "detalhes",
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

_COMPONENTES_TODOS = ["backend", "frontend", "schema"]


def _main() -> int:
    p = argparse.ArgumentParser(description="Aplica migrações / registra releases.")
    sub = p.add_subparsers(dest="cmd", required=True)

    p_apply = sub.add_parser("apply", help="aplica migrações pendentes e loga o evento")
    p_apply.add_argument("--origem", default="deploy")
    p_apply.add_argument(
        "--risco", default="todos", choices=["critica", "rotina", "melhoria", "todos"]
    )
    p_apply.add_argument("--usuario", default=None)
    p_apply.add_argument(
        "--sem-docs",
        action="store_true",
        help="válvula de emergência: aplica mesmo sem MUDANCA documentada",
    )

    p_pub = sub.add_parser("publicar", help="registra releases (manifestos) no Histórico")
    p_pub.add_argument(
        "--componentes",
        default="todos",
        help="'todos' ou CSV: backend,frontend,schema",
    )
    p_pub.add_argument("--usuario", default=None)

    args = p.parse_args()
    try:
        if args.cmd == "apply":
            st = apply_updates(
                riscos=_RISCO_CLI[args.risco],
                origem=args.origem,
                usuario=args.usuario,
                sem_docs=args.sem_docs,
            )
            print(json.dumps(st))
            return 0
        # publicar
        comps = (
            _COMPONENTES_TODOS
            if args.componentes.strip().lower() == "todos"
            else [c.strip() for c in args.componentes.split(",") if c.strip()]
        )
        publicadas = registrar_publicacao(comps, usuario=args.usuario)
        print(json.dumps({"ok": True, "releases_registradas": publicadas}))
        return 0
    except Exception as e:  # noqa: BLE001
        print(json.dumps({"ok": False, "error": str(e)}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(_main())
