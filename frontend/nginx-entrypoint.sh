#!/bin/sh
# Entrypoint do nginx — escolhe a config (TLS vs HTTP) conforme o certificado
# Let's Encrypt e recarrega periodicamente para assumir renovações.
set -e

DOMAIN="${DOMAIN:-siscom.casalm.com.br}"
CERT="/etc/letsencrypt/live/${DOMAIN}/fullchain.pem"
TLS_CONF="/etc/nginx/tls.conf"
HTTP_CONF="/etc/nginx/http.conf"
ACTIVE_CONF="/etc/nginx/conf.d/default.conf"

select_config() {
  if [ -f "$CERT" ]; then
    cp "$TLS_CONF" "$ACTIVE_CONF"
  else
    cp "$HTTP_CONF" "$ACTIVE_CONF"
  fi
}

# Aguarda (curto) o certificado do certbot na 1ª subida — o certbot roda em
# paralelo e emite via DNS-01. Se demorar, segue com HTTP e o loop abaixo
# troca para TLS assim que o certificado aparecer.
i=0
while [ ! -f "$CERT" ] && [ "$i" -lt 12 ]; do
  sleep 5
  i=$((i + 1))
done

select_config

# Entrypoint oficial do nginx prepara a config e inicia o nginx (daemon off).
/docker-entrypoint.sh nginx -g "daemon off;" &
NGINX_PID=$!

# Loop de recarga: quando o certificado surge ou é renovado (mtime muda),
# re-seleciona a config e recarrega o nginx.
reload_loop() {
  local last=""
  while :; do
    sleep 60
    local m=""
    [ -f "$CERT" ] && m=$(stat -c %Y "$CERT" 2>/dev/null || echo 0)
    if [ "$m" != "$last" ]; then
      select_config
      nginx -s reload 2>/dev/null || true
      last="$m"
    fi
  done
}
reload_loop &
RELOAD_PID=$!

trap 'kill -TERM $NGINX_PID 2>/dev/null || true; kill $RELOAD_PID 2>/dev/null || true; exit 0' TERM INT

wait $NGINX_PID