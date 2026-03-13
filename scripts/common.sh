#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

log_info() { echo "[INFO] $*"; }
log_warn() { echo "[WARN] $*"; }
log_err() { echo "[ERR] $*" >&2; }

if docker compose version >/dev/null 2>&1; then
  COMPOSE_BASE=(docker compose)
  COMPOSE_FLAVOR="v2"
elif command -v docker-compose >/dev/null 2>&1; then
  COMPOSE_BASE=(docker-compose)
  COMPOSE_FLAVOR="v1"
else
  log_err "Docker Compose not found (tried: docker compose, docker-compose)."
  exit 1
fi

read_env_value() {
  local key="$1"
  [[ -f .env ]] || return 0
  local line
  line="$(grep -E "^${key}=" .env | tail -n 1 || true)"
  line="${line#*=}"
  line="${line%\"}"
  line="${line#\"}"
  echo "$line"
}

is_enabled() {
  local value="${1:-}"
  value="${value,,}"
  [[ "$value" == "1" || "$value" == "true" || "$value" == "yes" || "$value" == "on" ]]
}

COMPOSE_PROJECT_NAME_VAL="${COMPOSE_PROJECT_NAME:-$(read_env_value COMPOSE_PROJECT_NAME)}"
COMPOSE_PROJECT_NAME_VAL="${COMPOSE_PROJECT_NAME_VAL:-vpn_admin_panel}"

COMPOSE_OPTS=(--project-name "$COMPOSE_PROJECT_NAME_VAL" -f docker-compose.yml)

ENABLE_TLS_PROXY_VAL="${ENABLE_TLS_PROXY:-$(read_env_value ENABLE_TLS_PROXY)}"
ENABLE_XRAY_PUBLIC_VAL="${ENABLE_XRAY_PUBLIC:-$(read_env_value ENABLE_XRAY_PUBLIC)}"

if is_enabled "$ENABLE_TLS_PROXY_VAL"; then
  [[ -f docker-compose.tls.yml ]] || { log_err "docker-compose.tls.yml not found"; exit 1; }
  COMPOSE_OPTS+=(-f docker-compose.tls.yml)
fi
if is_enabled "$ENABLE_XRAY_PUBLIC_VAL"; then
  [[ -f docker-compose.xray-public.yml ]] || { log_err "docker-compose.xray-public.yml not found"; exit 1; }
  COMPOSE_OPTS+=(-f docker-compose.xray-public.yml)
fi

COMPOSE=("${COMPOSE_BASE[@]}" "${COMPOSE_OPTS[@]}")
