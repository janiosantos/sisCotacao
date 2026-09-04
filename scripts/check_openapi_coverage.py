#!/usr/bin/env python
"""Checa a cobertura do OpenAPI contra as rotas /api registradas na aplicação.

Uso:
    python scripts/check_openapi_coverage.py [--strict] [--spec backend/openapi.json]

Requer DATABASE_URL/CATALOG_SECRET (a aplicação é criada para enumerar as rotas).
Sem `--strict`, apenas reporta a cobertura (não bloqueia). Com `--strict`,
sai com código 1 se houver rota /api pública/importante sem contrato.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

_RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_RAIZ))
sys.path.insert(0, str(_RAIZ / "backend"))

# Rotas que não precisam de contrato (auth, health, públicas sem payload).
_SKIP = (
    "/api/health",
    "/api/pronto",
    "/api/login",
    "/api/logout",
    "/api/primeiro-usuario",
    "/api/openapi.json",
    "/api/usuarios/atual",
)


def _normalizar(rule: str) -> str:
    # Flask <int:id> / <path:name> -> {id} / {name}
    return re.sub(r"<(?:\w+:)?([^>]+)>", r"{\1}", rule)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--strict", action="store_true")
    ap.add_argument("--spec", default=str(_RAIZ / "backend" / "openapi.json"))
    args = ap.parse_args()

    spec = json.loads(Path(args.spec).read_text(encoding="utf-8"))

    from catalog_server.app_factory import create_app

    app = create_app(bootstrap=False, start_workers=False)
    operacoes_app: set[tuple[str, str]] = set()
    for rule in app.url_map.iter_rules():
        path = _normalizar(rule.rule)
        if not path.startswith("/api/"):
            continue
        if path in _SKIP or path.startswith("/api/fornecedor/") or path.startswith("/api/publico/"):
            continue
        for method in (rule.methods or set()) - {"HEAD", "OPTIONS"}:
            operacoes_app.add((path, method.upper()))

    operacoes_spec: set[tuple[str, str]] = set()
    for path, item in spec.get("paths", {}).items():
        for method in item:
            if method.lower() in {"get", "post", "put", "patch", "delete"}:
                operacoes_spec.add((path, method.upper()))

    faltando = sorted(operacoes_app - operacoes_spec)
    cobertas = len(operacoes_app & operacoes_spec)
    total = len(operacoes_app)
    print(f"cobertura: {cobertas}/{total} rotas /api no OpenAPI")
    if faltando:
        print(f"sem contrato ({len(faltando)}):")
        for p in faltando[:60]:
            print("  ", p)
        if len(faltando) > 60:
            print(f"   ... e mais {len(faltando) - 60}")
    if args.strict and faltando:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())