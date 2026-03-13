#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT_DIR"

MODE="${1:-prod-like}"
if [[ ! "$MODE" =~ ^(dev|stage|prod-like)$ ]]; then
  echo "[ERR] Usage: ./install.sh [dev|stage|prod-like]"
  exit 1
fi

if [[ ! -f .env ]]; then
  cp .env.example .env
  echo "[INFO] .env created from .env.example"
fi

if grep -q '^API_TOKEN=admin-token$' .env; then
  echo "[WARN] API_TOKEN still uses default 'admin-token'. Change it before public rollout."
fi

./scripts/verify-release-readiness.sh
./scripts/doctor.sh "$MODE"
./deploy.sh "$MODE"
./scripts/post-deploy-check.sh

echo "[INFO] install flow complete"
