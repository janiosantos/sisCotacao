#!/usr/bin/env bash
# Smoke tests pós-deploy (Regra 12) — falha em qualquer checagem derruba o job.
# Uso: bash deployment/scripts/smoke.sh [BASE_URL]
#   BASE_URL padrão: http://localhost        (produção, após health gate)
#   Staging usa:     http://localhost:8081   (workflow Deploy Staging)
#
# Checagens de login exigem os secrets SMOKE_USER/SMOKE_PASS (usuário dedicado,
# perfil vendedor). Sem eles, o login é PULADO com aviso — as checagens abertas
# continuam obrigatórias.
#
# Portável de propósito: NÃO depende de python3/jq no host do runner
# (parse de JSON feito com sed/grep).

set -euo pipefail

BASE="${1:-http://localhost}"
fail() { echo "::error::SMOKE FALHOU: $1"; exit 1; }

# 1. Liveness do container backend
curl -fsS "$BASE/api/health" >/dev/null || fail "/api/health não respondeu 200"

# 2. Readiness real (banco acessível)
PRONTO=$(curl -fsS "$BASE/api/pronto") || fail "/api/pronto não respondeu 200"
echo "$PRONTO" | grep -q '"pronto"[^:]*: *true' || fail "/api/pronto sem pronto:true"

# 3. Login + status autenticado (somente com credenciais configuradas)
if [ -n "${SMOKE_USER:-}" ] && [ -n "${SMOKE_PASS:-}" ]; then
  RESP=$(curl -sS -X POST "$BASE/api/login" \
            -H 'Content-Type: application/json' \
            -d "{\"login\":\"$SMOKE_USER\",\"senha\":\"$SMOKE_PASS\"}") \
    || fail "login do usuário smoke falhou na requisição"
  echo "$RESP" | grep -q '"autenticado": *true\|"autenticado":true' \
    || fail "login recusado pelo servidor"
  TOKEN=$(echo "$RESP" | sed -n 's/.*"token":"\([^"]*\)".*/\1/p')
  [ -n "$TOKEN" ] || fail "login não retornou token"
  STATUS=$(curl -fsS "$BASE/api/sistema/status" -H "Authorization: Bearer $TOKEN") \
    || fail "/api/sistema/status falhou com token"
  echo "$STATUS" | grep -q '"atualizado"[^:]*: *true' \
    || fail "sistema/status informou migrações pendentes"
  echo "smoke: login + status OK"
else
  echo "::warning::SMOKE_USER/SMOKE_PASS ausentes — checagens de login PULADAS"
fi

# 4. Frontend servindo o shell da SPA
curl -fsS "$BASE/" | grep -q 'id="root"' || fail "frontend não servindo index.html"

echo "SMOKE OK ($BASE)"
