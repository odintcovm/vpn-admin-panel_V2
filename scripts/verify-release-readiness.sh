#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

echo "[check] shell syntax"
bash -n deploy.sh scripts/*.sh

echo "[check] base compose compatibility rules"
if rg -n '^name:' docker-compose.yml >/dev/null; then
  echo "[FAIL] docker-compose.yml contains top-level name"
  exit 1
fi
if rg -n '"443:443"' docker-compose.yml >/dev/null; then
  echo "[FAIL] base docker-compose.yml publishes 443"
  exit 1
fi
if ! rg -n '"80:80"' docker-compose.yml >/dev/null; then
  echo "[FAIL] base docker-compose.yml must publish 80:80"
  exit 1
fi

echo "[check] overrides"
rg -n '"443:443"' docker-compose.tls.yml >/dev/null
rg -n 'XRAY_PUBLIC_PORT' docker-compose.xray-public.yml >/dev/null

echo "[check] caddy routing"
rg -n '@sse path /api/events/stream\*' docker/caddy/Caddyfile.template >/dev/null
rg -n '@api path /api/\* /health' docker/caddy/Caddyfile.template >/dev/null
rg -n 'flush_interval -1' docker/caddy/Caddyfile.template >/dev/null

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
for key in COMPOSE_PROJECT_NAME APP_ENV DEV_ROLE_EMULATION SCHEMA_MANAGEMENT_MODE DOMAIN ENABLE_TLS_PROXY ENABLE_XRAY_PUBLIC XRAY_PUBLIC_PORT; do
  rg -n "^${key}=" .env.example >/dev/null || { echo "[FAIL] missing $key in .env.example"; exit 1; }
done

echo "[check] docs mention v1/v2 compose and host-443 coexistence"
rg -n 'docker-compose.*v1\.29\.2|docker compose.*v2' README.md >/dev/null
rg -n '443.*host Xray|host Xray.*443' README.md >/dev/null

echo "[OK] release-readiness static checks passed"
