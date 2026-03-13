#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

contains() {
  local pattern="$1" file="$2"
  grep -Eq "$pattern" "$file"
}

echo "[check] shell syntax"
bash -n deploy.sh install.sh scripts/*.sh

echo "[check] base compose compatibility rules"
if contains '^name:' docker-compose.yml; then
  echo "[FAIL] docker-compose.yml contains top-level name"
  exit 1
fi
if contains '"443:443"' docker-compose.yml; then
  echo "[FAIL] base docker-compose.yml publishes 443"
  exit 1
fi
if ! contains '"80:80"' docker-compose.yml; then
  echo "[FAIL] base docker-compose.yml must publish 80:80"
  exit 1
fi

echo "[check] required compose overlays"
for f in docker-compose.tls.yml docker-compose.xray-public.yml docker-compose.wg.yml docker-compose.avg.yml docker-compose.behind-ingress.yml; do
  [[ -f "$f" ]] || { echo "[FAIL] missing $f"; exit 1; }
done
contains '"443:443"' docker-compose.tls.yml
contains 'XRAY_PUBLIC_PORT' docker-compose.xray-public.yml

echo "[check] caddy routing"
contains '@sse path /api/events/stream\*' docker/caddy/Caddyfile.template
contains '@api path /api/\* /health' docker/caddy/Caddyfile.template
contains 'flush_interval -1' docker/caddy/Caddyfile.template

echo "[check] caddyfile matches template default :80"
python - <<'PY'
from pathlib import Path
tpl = Path('docker/caddy/Caddyfile.template').read_text()
cur = Path('docker/caddy/Caddyfile').read_text()
expected = tpl.replace('{$SITE_ADDR}', ':80')
if cur.strip() != expected.strip():
    raise SystemExit('Caddyfile diverges from template default :80 rendering')
print('ok')
PY

echo "[check] required env keys"
for key in COMPOSE_PROJECT_NAME APP_ENV DEV_ROLE_EMULATION SCHEMA_MANAGEMENT_MODE DEPLOY_MODE APP_PROVIDER PROVIDERS_ENABLED DOMAIN ENABLE_TLS_PROXY ENABLE_XRAY_PUBLIC ENABLE_WG_RUNTIME ENABLE_AVG_RUNTIME XRAY_PUBLIC_PORT AUTH_ENABLED AUTH_COOKIE_NAME AUTH_SESSION_TTL_HOURS ADMIN_USERNAME; do
  contains "^${key}=" .env.example || { echo "[FAIL] missing $key in .env.example"; exit 1; }
done

echo "[check] docs mention modes and provider/auth"
contains 'safe|full|behind-ingress' README.md
contains 'xray|wg|avg' README.md
contains 'login|logout|авторизац' README.md

echo "[OK] release-readiness static checks passed"
