#!/usr/bin/env bash
# Testa a CADEIA DE MIGRAÇÕES completa contra um PostgreSQL descartável
# (Regra 06): banco vazio -> head -> aplicação de pé respondendo /api/pronto.
# Tudo em containers: o host não precisa de python/docker-compose.
set -euo pipefail

RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
NET="ci-net-$$"
PG="ci-pg-$$"
URL="postgresql+psycopg://catalog:catalog@${PG}:5432/catalog"
IMAGE="${CI_BACKEND_IMAGE:-siscom-backend:latest}"

cleanup() {
  docker rm -f "$PG" >/dev/null 2>&1 || true
  docker network rm "$NET" >/dev/null 2>&1 || true
}
trap cleanup EXIT

docker network create "$NET" >/dev/null
echo "[migrations] postgres descartável subindo..."
docker run -d --name "$PG" --network "$NET" \
  --tmpfs /var/lib/postgresql/data:rw,noexec,nosuid,size=2g,nr_inodes=1048576 \
  -e POSTGRES_USER=catalog -e POSTGRES_PASSWORD=catalog -e POSTGRES_DB=catalog \
  postgres:16-alpine postgres -c fsync=off -c synchronous_commit=off \
  -c full_page_writes=off >/dev/null

for i in $(seq 1 30); do
  # O initdb sobe um servidor temporario antes de criar o banco solicitado.
  # Uma consulta real evita aceitar essa janela como readiness definitivo.
  if docker exec "$PG" psql -U catalog -d catalog -Atqc 'SELECT 1' >/dev/null 2>&1; then break; fi
  sleep 2
done
if ! docker exec "$PG" psql -U catalog -d catalog -Atqc 'SELECT 1' >/dev/null 2>&1; then
  echo "[migrations] PostgreSQL não ficou pronto; diagnóstico do container:"
  docker logs "$PG" 2>&1 || true
  df -h "$(docker info --format '{{.DockerRootDir}}')" || true
  exit 1
fi

# Código da BRANCH montado sobre a imagem (deps do pip já na imagem).
# Bootstrap fresco vazio->head:
echo "[migrations] bootstrap fresco (vazio -> head)..."
docker run --rm --network "$NET" \
  -v "${RAIZ}/backend:/app" -v "${RAIZ}/app:/app/app" -w /app \
  -e DATABASE_URL="$URL" -e AUTO_MIGRATE=0 -e APP_VERSION=ci \
  "$IMAGE" \
  python -m migrations apply

# Trio Migration+Banco+Backend: app de pé e readiness real:
echo "[migrations] app contra o schema resultante..."
docker run --rm --network "$NET" \
  -v "${RAIZ}/backend:/app" -v "${RAIZ}/app:/app/app" -w /app \
  -e DATABASE_URL="$URL" -e AUTO_MIGRATE=0 -e APP_VERSION=ci \
  "$IMAGE" \
  python -c "
from catalog_server.app_factory import create_app
c = create_app().test_client()
r = c.get('/api/pronto')
assert r.status_code == 200 and b'pronto' in r.data, r.data
print('pronto OK')
"

echo "[migrations] MIGRATIONS OK"
