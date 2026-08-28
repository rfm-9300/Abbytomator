#!/usr/bin/env bash
set -euo pipefail

# Runs on extractor-vps. Pulls the published image and recreates only
# Abbitomator. Does not `down` the stack (that drops web_proxy and breaks
# Extractor Caddy). Leaves .env and abbitomator_data untouched.

APP_DIR="${APP_DIR:-$HOME/abbitomator}"
COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.prod.yml}"
TAG="${TAG:-latest}"
REGISTRY_IMAGE="${REGISTRY_IMAGE:-ghcr.io/rfm-9300/abbytomator}"
HEALTH_RETRIES="${HEALTH_RETRIES:-30}"
HEALTH_SLEEP_SECONDS="${HEALTH_SLEEP_SECONDS:-2}"

cd "$APP_DIR"

if [[ -n "${GHCR_TOKEN:-}" ]]; then
  echo "${GHCR_TOKEN}" | docker login ghcr.io -u "${GHCR_USERNAME:-github}" --password-stdin
fi

export TAG
echo "Deploying ${REGISTRY_IMAGE}:${TAG}"

docker compose -f "${COMPOSE_FILE}" pull
docker compose -f "${COMPOSE_FILE}" up -d --remove-orphans

logout_ghcr() {
  if [[ -n "${GHCR_TOKEN:-}" ]]; then
    docker logout ghcr.io >/dev/null 2>&1 || true
  fi
}
trap logout_ghcr EXIT

container_ip() {
  local cid
  cid="$(docker compose -f "${COMPOSE_FILE}" ps -q web)"
  docker inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{println}}{{end}}' "${cid}" \
    | awk 'NF { print; exit }'
}

echo "Waiting for /health..."
ip=""
for _ in $(seq 1 "${HEALTH_RETRIES}"); do
  ip="$(container_ip || true)"
  if [[ -n "${ip}" ]] && curl -fsS "http://${ip}:8001/health" >/dev/null; then
    echo "Health check passed at ${ip}:8001"
    docker compose -f "${COMPOSE_FILE}" ps
    exit 0
  fi
  sleep "${HEALTH_SLEEP_SECONDS}"
done

echo "Health check failed after ${HEALTH_RETRIES} attempts" >&2
docker compose -f "${COMPOSE_FILE}" ps >&2 || true
docker compose -f "${COMPOSE_FILE}" logs --tail=100 web >&2 || true
exit 1
