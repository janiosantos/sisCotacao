#!/usr/bin/env bash
# Suíte pytest do backend (backend/tests) contra PostgreSQL descartável.
# O conftest aplica o schema via runner e zera as tabelas entre testes.
set -euo pipefail

RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
NET="ci-net-$$"
PG="ci-pg-$$"
URL="postgresql+psycopg://catalog:catalog@${PG}:5432/catalog"

cleanup() {
  docker rm -f "$PG" >/dev/null 2>&1 || true
  docker network rm "$NET" >/dev/null 2>&1 || true
}
trap cleanup EXIT

docker network create "$NET" >/dev/null
echo "[backend] postgres descartável subindo..."
docker run -d --name "$PG" --network "$NET" \
  -e POSTGRES_USER=catalog -e POSTGRES_PASSWORD=catalog -e POSTGRES_DB=catalog \
  postgres:16-alpine >/dev/null

for i in $(seq 1 30); do
  if docker exec "$PG" pg_isready -U catalog >/dev/null 2>&1; then break; fi
  sleep 2
done

# pytest instalado ad-hoc no container efêmero (não altera a imagem).
echo "[backend] pytest backend/tests ..."
docker run --rm --network "$NET" \
  -v "${RAIZ}/backend:/app" -v "${RAIZ}/app:/app/app" -w /app \
  -e DATABASE_URL="$URL" -e TEST_PG_URL="$URL" \
  siscom-backend:latest \
  bash -c "pip install -q pytest && python -m pytest tests -q"

echo "[backend] BACKEND OK"
