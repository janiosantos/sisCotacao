#!/usr/bin/env bash
# Instala e registra um GitHub Actions self-hosted runner no servidor de produção.
# O runner faz outbound HTTPS para o GitHub (sem abrir porta de entrada) e executa
# o pipeline .github/workflows/deploy.yml localmente, no próprio servidor.
#
# Uso:  bash scripts/ci/setup-runner.sh <runner_registration_token>
# O token é gerado em: GitHub -> janiosantos/sisCotacao -> Settings -> Actions -> Runners -> New runner
# (atenção: tokens de registro expiram em ~1h).
set -euo pipefail

# O runner do GitHub recusa rodar como root sem esta variável.
export RUNNER_ALLOW_RUNASROOT=1

RUNNER_DIR=/home/jpsantos/actions-runner
REPO_URL=https://github.com/janiosantos/sisCotacao
LABEL=siscom-prod
RUNNER_VERSION=2.321.0

TOKEN="${1:-${RUNNER_TOKEN:-}}"
if [ -z "$TOKEN" ]; then
  echo "ERRO: informe o token de registro do runner." >&2
  echo "Uso: $0 <runner_registration_token>" >&2
  exit 1
fi

# Dependência do runner (libicu) e git já devem existir.
command -v git >/dev/null 2>&1 || { echo "git não encontrado"; exit 1; }
if command -v apt-get >/dev/null 2>&1; then
  apt-get update -y >/dev/null 2>&1 || true
  apt-get install -y libicu-dev >/dev/null 2>&1 || true
fi

mkdir -p "$RUNNER_DIR" && cd "$RUNNER_DIR"

if [ -f .runner ]; then
  echo "Runner já configurado em $RUNNER_DIR (use ./svc.sh para gerenciar)."
else
  curl -fsSL -o act.tar.gz \
    "https://github.com/actions/runner/releases/download/v${RUNNER_VERSION}/actions-runner-linux-x64-${RUNNER_VERSION}.tar.gz"
  tar xzf act.tar.gz && rm -f act.tar.gz

  ./config.sh --url "$REPO_URL" --token "$TOKEN" \
    --name siscom-prod --labels "$LABEL" --work _work --unattended

  ./svc.sh install
  ./svc.sh start
  echo "Runner 'siscom-prod' registrado e iniciado como serviço."
fi

# Diretórios usados pelo pipeline.
mkdir -p /home/jpsantos/siscom/backups /home/jpsantos/siscom/img
echo "Pronto. Verifique em GitHub -> Settings -> Actions -> Runners se 'siscom-prod' está online (Idle)."
