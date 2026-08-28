#!/usr/bin/env bash
set -euo pipefail

REGISTRY_IMAGE="${REGISTRY_IMAGE:-ghcr.io/rfm-9300/abbytomator}"
TAG="${TAG:-latest}"
PLATFORM="${PLATFORM:-linux/amd64}"
FULL_IMAGE_NAME="${REGISTRY_IMAGE}:${TAG}"

echo "Building ${FULL_IMAGE_NAME} for ${PLATFORM}..."
docker build --platform "${PLATFORM}" -t "${FULL_IMAGE_NAME}" .

echo "Pushing ${FULL_IMAGE_NAME}..."
docker push "${FULL_IMAGE_NAME}"

echo "Image pushed: ${FULL_IMAGE_NAME}"
echo
echo "Production deploys normally run from GitHub Actions on push to main."
echo "Manual VPS steps (emergency fallback):"
echo "  ssh extractor-vps 'mkdir -p ~/abbitomator'"
echo "  scp docker-compose.prod.yml scripts/remote-deploy.sh extractor-vps:~/abbitomator/"
echo "  ssh extractor-vps 'chmod +x ~/abbitomator/remote-deploy.sh && TAG=${TAG} ~/abbitomator/remote-deploy.sh'"
