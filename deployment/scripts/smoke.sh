#!/usr/bin/env bash
# Smoke tests pós-deploy (Regra 12) — falha em qualquer checagem derruba o job.
# Uso: bash deployment/scripts/smoke.sh [BASE_URL]
#   BASE_URL padrão: http://localhost        (produção, após health gate)
#   Staging usa:     http://localhost:8081   (workflow Deploy Staging)
#
# Checagens de login exigem os secrets SMOKE_USER/SMOKE_PASS (usuário dedicado,
# perfil vendedor). Sem eles, o login é PULADO com aviso — as checagens abertas
# continuam obrigatórias.

set -euo pipefail

BASE="${1:-http://localhost}"
fail() { echo "::error::SMOKE FALHOU: $1"; exit 1; }

# 1. Liveness do container backend
curl -fsS "$BASE/api/health" >/dev/null || fail "/api/health não respondeu 200"

# 2. Readiness real (banco acessível)
PRONTO=$(curl -fsS "$BASE/api/pronto") || fail "/api/pronto não respondeu 200"
echo "$PRONTO" | grep -q '"pronto": *true\|"pronto":true' || fail "/api/pronto sem pronto:true"

# 3. Login + status autenticado (somente com credenciais configuradas)
if [ -n "${SMOKE_USER:-}" ] && [ -n "${SMOKE_PASS:-}" ]; then
  TOKEN=$(curl -fsS -X POST "$BASE/api/login" \
            -H 'Content-Type: application/json' \
            -d "{\"login\":\"$SMOKE_USER\",\"senha\":\"$SMOKE_PASS\"}" \
          | python3 -c 'import sys,json;print(json.load(sys.stdin).get("token",""))') \
    || fail "login do usuário smoke falhou"
  [ -n "$TOKEN" ] || fail "login não retornou token"
  STATUS=$(curl -fsS "$BASE/api/sistema/status" -H "Authorization: Bearer $TOKEN") \
    || fail "/api/sistema/status falhou com token"
  echo "$STATUS" | python3 -c 'import sys,json;d=json.load(sys.stdin);sys.exit(0 if d.get("atualizado") else 1)' \
    || fail "sistema/status informou migrações pendentes"
  echo "smoke: login + status OK"
else
  echo "::warning::SMOKE_USER/SMOKE_PASS ausentes — checagens de login PULADAS"
fi

# 4. Frontend servindo o shell da SPA
curl -fsS "$BASE/" | grep -q 'id="root"' || fail "frontend não servindo index.html"

echo "SMOKE OK ($BASE)"
