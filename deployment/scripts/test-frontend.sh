#!/usr/bin/env bash
# Typecheck + build do frontend em container node (sem sujar o host).
set -euo pipefail

RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

echo "[frontend] npm ci + typecheck + build ..."
docker run --rm \
  -v "${RAIZ}/frontend:/app" -w /app \
  node:22-alpine sh -c "npm ci --no-audit --no-fund && npm run typecheck && npm run build"

echo "[frontend] FRONTEND OK"
