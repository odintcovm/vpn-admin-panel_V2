#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT_DIR"

MODE="${1:-safe}"
PROVIDER="${2:-xray}"

if [[ ! "$MODE" =~ ^(safe|full|behind-ingress)$ ]]; then
  echo "[ERR] Usage: ./install.sh [safe|full|behind-ingress] [xray|wg|avg|mock]"
  exit 1
fi
if [[ ! "$PROVIDER" =~ ^(xray|wg|avg|mock)$ ]]; then
  echo "[ERR] provider must be one of: xray|wg|avg|mock"
  exit 1
fi

if ! command -v docker >/dev/null 2>&1; then
  echo "[ERR] Docker not found"
  exit 1
fi
if ! docker compose version >/dev/null 2>&1 && ! command -v docker-compose >/dev/null 2>&1; then
  echo "[ERR] Docker Compose not found"
  exit 1
fi

[[ -f .env ]] || cp .env.example .env

set_kv() {
  local key="$1" val="$2"
  if grep -q "^${key}=" .env; then
    sed -i "s#^${key}=.*#${key}=${val}#" .env
  else
    echo "${key}=${val}" >> .env
  fi
}

set_kv APP_PROVIDER "$PROVIDER"
set_kv DEPLOY_MODE "$MODE"
set_kv ENABLE_WG_RUNTIME true
set_kv ENABLE_AVG_RUNTIME true
set_kv AUTH_ENABLED true
set_kv AUTH_COOKIE_SECURE false
set_kv ADMIN_USERNAME "${ADMIN_USERNAME:-admin}"

if [[ -n "${ADMIN_PASSWORD:-}" ]]; then
  set_kv ADMIN_PASSWORD "$ADMIN_PASSWORD"
fi
if [[ "$MODE" == "full" ]]; then
  set_kv ENABLE_TLS_PROXY true
  set_kv ENABLE_XRAY_PUBLIC true
fi
if [[ "$MODE" == "safe" ]]; then
  set_kv ENABLE_TLS_PROXY false
  set_kv ENABLE_XRAY_PUBLIC false
fi
if [[ "$MODE" == "behind-ingress" ]]; then
  set_kv ENABLE_TLS_PROXY false
  set_kv ENABLE_XRAY_PUBLIC false
fi

./scripts/verify-release-readiness.sh
./scripts/doctor.sh "$MODE"
./deploy.sh "$MODE"
./scripts/post-deploy-check.sh
