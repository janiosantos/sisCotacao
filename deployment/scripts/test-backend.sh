#!/usr/bin/env bash
# Suíte pytest do backend (backend/tests) contra PostgreSQL descartável.
# O conftest aplica o schema via runner e zera as tabelas entre testes.
set -euo pipefail

RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
NET="ci-net-$$"
PG="ci-pg-$$"
IMAGE="${CI_BACKEND_IMAGE:-siscom-backend:pytest-$$}"
OWN_IMAGE=0
if [ -z "${CI_BACKEND_IMAGE:-}" ]; then
  OWN_IMAGE=1
fi
URL="postgresql+psycopg://catalog:catalog@${PG}:5432/catalog"
read -r -a TEST_TARGETS <<< "${BACKEND_TEST_TARGETS:-backend/tests}"

cleanup() {
  docker rm -f "$PG" >/dev/null 2>&1 || true
  docker network rm "$NET" >/dev/null 2>&1 || true
  if [ "$OWN_IMAGE" = "1" ]; then
    docker image rm "$IMAGE" >/dev/null 2>&1 || true
  fi
}
trap cleanup EXIT

docker network create "$NET" >/dev/null
echo "[backend] postgres descartável subindo..."
docker run -d --name "$PG" --network "$NET" \
  --tmpfs /var/lib/postgresql/data:rw,noexec,nosuid,size=2g,nr_inodes=1048576 \
  -e POSTGRES_USER=catalog -e POSTGRES_PASSWORD=catalog -e POSTGRES_DB=catalog \
  postgres:16-alpine postgres -c fsync=off -c synchronous_commit=off \
  -c full_page_writes=off >/dev/null

for i in $(seq 1 30); do
  if docker exec "$PG" pg_isready -U catalog >/dev/null 2>&1; then break; fi
  sleep 2
done
if ! docker exec "$PG" pg_isready -U catalog >/dev/null 2>&1; then
  echo "[backend] PostgreSQL não ficou pronto; diagnóstico do container:"
  docker logs "$PG" 2>&1 || true
  df -h "$(docker info --format '{{.DockerRootDir}}')" || true
  exit 1
fi

# A imagem de testes contém a mesma árvore do repositório e as dependências de
# desenvolvimento; a imagem de produção continua sem pytest por padrão.
echo "[backend] pytest backend/tests ..."
if [ "$OWN_IMAGE" = "1" ]; then
  docker build --quiet \
    --build-arg INSTALL_TEST_DEPS=1 \
    -t "$IMAGE" \
    -f "$RAIZ/backend/Dockerfile" "$RAIZ" >/dev/null
fi

docker run --rm --network "$NET" \
  -e DATABASE_URL="$URL" -e TEST_PG_URL="$URL" \
  "$IMAGE" \
  python -m pytest "${TEST_TARGETS[@]}" -q

echo "[backend] BACKEND OK"
