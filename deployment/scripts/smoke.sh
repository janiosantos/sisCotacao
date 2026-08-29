#!/usr/bin/env bash
# Smoke tests pós-deploy (Regra 12) — falha em qualquer checagem derruba o job.
# Uso: bash deployment/scripts/smoke.sh [BASE_URL]
#   BASE_URL padrão: http://localhost        (produção, após health gate)
#   Staging usa:     http://localhost:8081   (workflow Deploy Staging)
#
# Tolerante a TLS: com HTTPS ativo (Let's Encrypt), a porta 80 redireciona;
# as checagens tentam https:// (inseguro, certificado válido p/ o domínio mas
# não para localhost) e caem para http:// quando o 443 ainda não existe.
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

# Deriva variantes http/https do BASE (host[:porta]).
if [[ "$BASE" == https://* ]]; then
  HTTPS_BASE="$BASE"
  HTTP_BASE="${BASE/https:\/\//http:\/\/}"
else
  HTTP_BASE="$BASE"
  HTTPS_BASE="${BASE/http:\/\//https:\/\/}"
fi

# GET que responde por https (inseguro) ou cai para http — imprime o corpo.
get() { # $1 = path, demais args = flags do curl (ex.: -H "Authorization: ...")
  local path="$1"; shift
  local body
  body=$(curl -ksS --max-time 8 "${HTTPS_BASE}${path}" "$@" 2>/dev/null) && { printf '%s' "$body"; return 0; }
  body=$(curl -fsS --max-time 8 "${HTTP_BASE}${path}" "$@" 2>/dev/null) && { printf '%s' "$body"; return 0; }
  return 1
}
# POST JSON por https (inseguro) ou http — imprime o corpo.
post() { # $1 = path, $2 = json
  local body
  body=$(curl -ksS --max-time 8 -X POST "${HTTPS_BASE}$1" -H 'Content-Type: application/json' -d "$2" 2>/dev/null) \
    && { printf '%s' "$body"; return 0; }
  body=$(curl -fsS --max-time 8 -X POST "${HTTP_BASE}$1" -H 'Content-Type: application/json' -d "$2" 2>/dev/null) \
    && { printf '%s' "$body"; return 0; }
  return 1
}

# 1. Liveness do container backend
get "/api/health" >/dev/null || fail "/api/health não respondeu 2xx"

# 2. Readiness real (banco acessível)
PRONTO=$(get "/api/pronto") || fail "/api/pronto não respondeu 2xx"
echo "$PRONTO" | grep -q '"pronto"[^:]*: *true' || fail "/api/pronto sem pronto:true"

# 3. Login + status autenticado (somente com credenciais configuradas)
if [ -n "${SMOKE_USER:-}" ] && [ -n "${SMOKE_PASS:-}" ]; then
  RESP=$(post "/api/login" "{\"login\":\"$SMOKE_USER\",\"senha\":\"$SMOKE_PASS\"}") \
    || fail "login do usuário smoke falhou na requisição"
  echo "$RESP" | grep -q '"autenticado": *true\|"autenticado":true' \
    || fail "login recusado pelo servidor"
  TOKEN=$(echo "$RESP" | sed -n 's/.*"token":"\([^"]*\)".*/\1/p')
  [ -n "$TOKEN" ] || fail "login não retornou token"
  STATUS=$(get "/api/sistema/status" -H "Authorization: Bearer $TOKEN") \
    || fail "/api/sistema/status falhou com token"
  echo "$STATUS" | grep -q '"atualizado"[^:]*: *true' \
    || fail "sistema/status informou migrações pendentes"
  echo "smoke: login + status OK"
else
  echo "::warning::SMOKE_USER/SMOKE_PASS ausentes — checagens de login PULADAS"
fi

# 4. Frontend servindo o shell da SPA
get "/" | grep -q 'id="root"' || fail "frontend não servindo index.html"

echo "SMOKE OK ($BASE)"