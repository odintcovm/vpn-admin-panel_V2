#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT_DIR"

MODE="${1:-prod-like}"
if [[ ! "$MODE" =~ ^(dev|stage|prod-like)$ ]]; then
  echo "[ERR] Usage: ./deploy.sh [dev|stage|prod-like]"
  exit 1
fi

if ! command -v docker >/dev/null 2>&1; then
  echo "[ERR] Docker not found. Install Docker Engine first."
  exit 1
fi

if docker compose version >/dev/null 2>&1; then
  COMPOSE=(docker compose)
elif command -v docker-compose >/dev/null 2>&1; then
  COMPOSE=(docker-compose)
else
  echo "[ERR] Docker Compose not found."
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

case "$MODE" in
  dev)
    set_env_value APP_ENV development
    set_env_value DEV_ROLE_EMULATION true
    set_env_value SCHEMA_MANAGEMENT_MODE bootstrap
    ;;
  stage)
    set_env_value APP_ENV staging
    set_env_value DEV_ROLE_EMULATION false
    set_env_value SCHEMA_MANAGEMENT_MODE alembic
    ;;
  prod-like)
    set_env_value APP_ENV production
    set_env_value DEV_ROLE_EMULATION false
    set_env_value SCHEMA_MANAGEMENT_MODE alembic
    ;;
esac

set_env_value APP_PROVIDER xray
set_env_value DATABASE_URL sqlite:///./data/data.db
set_env_value XRAY_PUBLIC_PORT "$(grep -E '^XRAY_PUBLIC_PORT=' .env | cut -d'=' -f2- || echo 8443)"

DOMAIN="$(grep -E '^DOMAIN=' .env | cut -d'=' -f2- || true)"
SITE_ADDR="${DOMAIN:-:80}"
sed "s/{\$SITE_ADDR}/${SITE_ADDR}/g" docker/caddy/Caddyfile.template > docker/caddy/Caddyfile

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
if [[ -n "${DOMAIN}" ]]; then
  PANEL_URL="https://${DOMAIN}"
fi

cat <<OUT

=== Deploy complete ===
Mode: ${MODE}
Panel URL: ${PANEL_URL}
API URL: ${PANEL_URL}/api
Logs: ./scripts/logs.sh [service]

Next operations:
  ./scripts/health-check.sh
  ./scripts/backup.sh
  ./scripts/update.sh
  ./scripts/restart.sh
  ./scripts/restore.sh <backup_file>

TLS note:
  - DOMAIN set: Caddy requests certificates automatically.
  - DOMAIN empty: self-host mode over HTTP (:80) without TLS automation.
OUT
