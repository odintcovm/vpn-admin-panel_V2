#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT_DIR"

MODE="${1:-safe}"
if [[ ! "$MODE" =~ ^(safe|full|behind-ingress|dev|stage|prod-like)$ ]]; then
  echo "[ERR] Usage: ./deploy.sh [safe|full|behind-ingress|dev|stage|prod-like]"
  exit 1
fi

if ! command -v docker >/dev/null 2>&1; then
  echo "[ERR] Docker not found. Install Docker Engine first."
  exit 1
fi

[[ -f .env ]] || cp .env.example .env

set_env_value() {
  local key="$1" value="$2"
  if grep -q "^${key}=" .env; then
    sed -i "s#^${key}=.*#${key}=${value}#" .env
  else
    echo "${key}=${value}" >> .env
  fi
}

read_env_value() {
  local key="$1"
  local line
  line="$(grep -E "^${key}=" .env | tail -n 1 || true)"
  echo "${line#*=}"
}

env_or_default() {
  local key="$1" default="$2"
  local value
  value="$(read_env_value "$key")"
  if [[ -z "$value" ]]; then
    echo "$default"
  else
    echo "$value"
  fi
}

case "$MODE" in
  dev)
    set_env_value APP_ENV development
    set_env_value DEV_ROLE_EMULATION true
    set_env_value SCHEMA_MANAGEMENT_MODE bootstrap
    set_env_value DEPLOY_MODE safe
    set_env_value ENABLE_TLS_PROXY false
    set_env_value ENABLE_XRAY_PUBLIC false
    ;;
  stage)
    set_env_value APP_ENV staging
    set_env_value DEV_ROLE_EMULATION false
    set_env_value SCHEMA_MANAGEMENT_MODE alembic
    set_env_value DEPLOY_MODE safe
    ;;
  prod-like|safe)
    set_env_value APP_ENV production
    set_env_value DEV_ROLE_EMULATION false
    set_env_value SCHEMA_MANAGEMENT_MODE alembic
    set_env_value DEPLOY_MODE safe
    set_env_value ENABLE_TLS_PROXY false
    set_env_value ENABLE_XRAY_PUBLIC false
    ;;
  full)
    set_env_value APP_ENV production
    set_env_value DEV_ROLE_EMULATION false
    set_env_value SCHEMA_MANAGEMENT_MODE alembic
    set_env_value DEPLOY_MODE full
    set_env_value ENABLE_TLS_PROXY true
    set_env_value ENABLE_XRAY_PUBLIC true
    ;;
  behind-ingress)
    set_env_value APP_ENV production
    set_env_value DEV_ROLE_EMULATION false
    set_env_value SCHEMA_MANAGEMENT_MODE alembic
    set_env_value DEPLOY_MODE behind-ingress
    set_env_value ENABLE_TLS_PROXY false
    set_env_value ENABLE_XRAY_PUBLIC false
    ;;
esac

set_env_value COMPOSE_PROJECT_NAME "vpn_admin_panel"
set_env_value APP_PROVIDER "$(env_or_default APP_PROVIDER xray)"
set_env_value PROVIDERS_ENABLED "$(env_or_default PROVIDERS_ENABLED xray,wg,avg,mock)"
set_env_value DATABASE_URL sqlite:///./data/data.db
set_env_value XRAY_PUBLIC_PORT "$(env_or_default XRAY_PUBLIC_PORT 8443)"
set_env_value WG_PUBLIC_PORT "$(env_or_default WG_PUBLIC_PORT 51820)"
set_env_value ENABLE_TLS_PROXY "$(env_or_default ENABLE_TLS_PROXY false)"
set_env_value ENABLE_XRAY_PUBLIC "$(env_or_default ENABLE_XRAY_PUBLIC false)"
set_env_value ENABLE_WG_RUNTIME "$(env_or_default ENABLE_WG_RUNTIME true)"
set_env_value ENABLE_AVG_RUNTIME "$(env_or_default ENABLE_AVG_RUNTIME true)"
set_env_value AUTH_ENABLED "$(env_or_default AUTH_ENABLED true)"
set_env_value AUTH_COOKIE_NAME "$(env_or_default AUTH_COOKIE_NAME vpn_admin_session)"
set_env_value AUTH_SESSION_TTL_HOURS "$(env_or_default AUTH_SESSION_TTL_HOURS 24)"
set_env_value AUTH_COOKIE_SECURE "$(env_or_default AUTH_COOKIE_SECURE false)"
set_env_value ADMIN_USERNAME "$(env_or_default ADMIN_USERNAME admin)"

DOMAIN="$(read_env_value DOMAIN)"
ENABLE_TLS_PROXY="$(env_or_default ENABLE_TLS_PROXY false)"
ENABLE_XRAY_PUBLIC="$(env_or_default ENABLE_XRAY_PUBLIC false)"
ENABLE_WG_RUNTIME="$(env_or_default ENABLE_WG_RUNTIME true)"
ENABLE_AVG_RUNTIME="$(env_or_default ENABLE_AVG_RUNTIME true)"
XRAY_PUBLIC_PORT="$(env_or_default XRAY_PUBLIC_PORT 8443)"

if [[ "$ENABLE_XRAY_PUBLIC" == "true" && ! "$XRAY_PUBLIC_PORT" =~ ^[0-9]+$ ]]; then
  echo "[ERR] XRAY_PUBLIC_PORT must be numeric when ENABLE_XRAY_PUBLIC=true"
  exit 1
fi

if [[ "$MODE" == "full" && -z "$DOMAIN" ]]; then
  echo "[ERR] full mode requires DOMAIN for TLS"
  exit 1
fi

if [[ "$ENABLE_TLS_PROXY" == "true" && -z "$DOMAIN" ]]; then
  echo "[WARN] ENABLE_TLS_PROXY=true but DOMAIN is empty. Falling back to HTTP :80 site address."
fi

if [[ "$ENABLE_TLS_PROXY" == "true" && -n "$DOMAIN" ]]; then
  SITE_ADDR="$DOMAIN"
else
  SITE_ADDR=":80"
fi
sed "s/{\$SITE_ADDR}/${SITE_ADDR}/g" docker/caddy/Caddyfile.template > docker/caddy/Caddyfile

source scripts/common.sh

echo "[INFO] Mode: ${MODE}"
echo "[INFO] Compose flavor: ${COMPOSE_FLAVOR}"
echo "[INFO] Compose project: ${COMPOSE_PROJECT_NAME_VAL}"
echo "[INFO] Compose files: ${COMPOSE_FILES_SUMMARY}"
echo "[INFO] Active provider: $(read_env_value APP_PROVIDER)"

if [[ "$ENABLE_TLS_PROXY" == "true" ]]; then
  echo "[INFO] TLS override enabled: docker-compose.tls.yml"
fi
if [[ "$ENABLE_XRAY_PUBLIC" == "true" ]]; then
  echo "[INFO] Xray public override enabled: docker-compose.xray-public.yml (${XRAY_PUBLIC_PORT}:8443)"
fi
if [[ "$ENABLE_WG_RUNTIME" == "true" ]]; then
  echo "[INFO] WG runtime enabled"
fi
if [[ "$ENABLE_AVG_RUNTIME" == "true" ]]; then
  echo "[INFO] AVG runtime enabled"
fi

echo "[1/5] Build & start services..."
"${COMPOSE[@]}" up -d --build

echo "[2/5] Wait for API health..."
for i in {1..45}; do
  if "${COMPOSE[@]}" exec -T api python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=3)" >/dev/null 2>&1; then
    break
  fi
  sleep 2
  if [[ "$i" -eq 45 ]]; then
    echo "[ERR] API health timeout"
    exit 1
  fi
done

echo "[3/5] Apply migrations..."
"${COMPOSE[@]}" exec -T api sh -lc 'PYTHONPATH=. alembic upgrade head'

echo "[4/5] Seed data (idempotent)..."
"${COMPOSE[@]}" exec -T api python - <<'PY'
from app.db.database import SessionLocal
from app.services.services import seed_if_empty
s = SessionLocal()
try:
    seed_if_empty(s)
finally:
    s.close()
print('seed: ok')
PY

echo "[5/5] Runtime status"
"${COMPOSE[@]}" ps

HOST_IP="$(hostname -I | awk '{print $1}')"
PANEL_URL="http://${HOST_IP}"
if [[ "$ENABLE_TLS_PROXY" == "true" && -n "$DOMAIN" ]]; then
  PANEL_URL="https://${DOMAIN}"
fi

cat <<OUT

=== Deploy complete ===
Mode: ${MODE}
Compose flavor: ${COMPOSE_FLAVOR}
Compose project: ${COMPOSE_PROJECT_NAME_VAL}
Panel URL: ${PANEL_URL}
API URL: ${PANEL_URL}/api
Health URL (proxy): ${PANEL_URL}/health

Enabled runtime options:
  ENABLE_TLS_PROXY=${ENABLE_TLS_PROXY}
  ENABLE_XRAY_PUBLIC=${ENABLE_XRAY_PUBLIC}
  ENABLE_WG_RUNTIME=${ENABLE_WG_RUNTIME}
  ENABLE_AVG_RUNTIME=${ENABLE_AVG_RUNTIME}
  XRAY_PUBLIC_PORT=${XRAY_PUBLIC_PORT}

Logs:
  ./scripts/logs.sh [service]

Next operations:
  ./scripts/post-deploy-check.sh
  ./scripts/health-check.sh
  ./scripts/backup.sh
  ./scripts/update.sh
  ./scripts/restart.sh
  ./scripts/restore.sh <backup_file>

Safety notes:
  - safe mode keeps panel independent from host 443 ownership
  - for hosts with existing ingress use behind-ingress mode
OUT
