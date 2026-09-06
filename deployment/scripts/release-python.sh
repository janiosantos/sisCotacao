#!/usr/bin/env bash
set -euo pipefail

# Release validation needs only the Python standard library. Prefer the host
# interpreter, but keep a Docker fallback for minimal/self-hosted runners.
if [ "${RELEASE_PYTHON_FORCE_DOCKER:-0}" != "1" ]; then
  if command -v python3 >/dev/null 2>&1; then
    exec python3 "$@"
  fi
  if command -v python >/dev/null 2>&1; then
    exec python "$@"
  fi
fi

if ! command -v docker >/dev/null 2>&1; then
  echo "ERRO: Python 3 e Docker nao estao disponiveis no runner." >&2
  exit 127
fi

workspace="${GITHUB_WORKSPACE:-$PWD}"
if [ -n "${RELEASE_PYTHON_IMAGE:-}" ]; then
  python_image="$RELEASE_PYTHON_IMAGE"
elif docker image inspect siscom-backend:latest >/dev/null 2>&1; then
  # The runner is also the application host, so this image is normally
  # available and avoids making release validation depend on Docker Hub.
  python_image="siscom-backend:latest"
else
  python_image="python:3.14-slim"
fi
docker_args=(
  run --rm -i
  --volume "$workspace:/workspace:ro"
  --workdir /workspace
)

# GITHUB_OUTPUT lives outside the checkout. Mount its directory when an inline
# validator needs to append outputs for subsequent workflow steps.
if [ -n "${GITHUB_OUTPUT:-}" ]; then
  output_dir="$(dirname "$GITHUB_OUTPUT")"
  docker_args+=(--volume "$output_dir:$output_dir")
fi

for name in \
  RELEASE_GIT_TAGS RELEASE_VERSION GITHUB_OUTPUT CANDIDATE_SHA \
  STAGING_RUN_ID STAGING_RUN_ATTEMPT GH_TOKEN GH_API_URL GH_REPOSITORY; do
  if [ "${!name+x}" = "x" ]; then
    docker_args+=(--env "$name")
  fi
done

exec docker "${docker_args[@]}" "$python_image" python "$@"
