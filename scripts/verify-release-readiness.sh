#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

find_text() {
  local pattern="$1" file="$2"
  if command -v rg >/dev/null 2>&1; then
    rg -n "$pattern" "$file" >/dev/null
  else
    grep -En "$pattern" "$file" >/dev/null
  fi
}

echo "[check] shell syntax"
bash -n deploy.sh install.sh scripts/*.sh

echo "[check] base compose compatibility rules"
if find_text '^name:' docker-compose.yml; then
  echo "[FAIL] docker-compose.yml contains top-level name"
  exit 1
fi
if find_text '"443:443"' docker-compose.yml; then
  echo "[FAIL] base docker-compose.yml publishes 443"
  exit 1
fi
if ! find_text '"80:80"' docker-compose.yml; then
  echo "[FAIL] base docker-compose.yml must publish 80:80"
  exit 1
fi

echo "[check] overrides"
find_text '"443:443"' docker-compose.tls.yml
find_text 'XRAY_PUBLIC_PORT' docker-compose.xray-public.yml

echo "[check] caddy routing"
find_text '@sse path /api/events/stream\*' docker/caddy/Caddyfile.template
find_text '@api path /api/\* /health' docker/caddy/Caddyfile.template
find_text 'flush_interval -1' docker/caddy/Caddyfile.template

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
for key in COMPOSE_PROJECT_NAME APP_ENV DEV_ROLE_EMULATION SCHEMA_MANAGEMENT_MODE DOMAIN ENABLE_TLS_PROXY ENABLE_XRAY_PUBLIC XRAY_PUBLIC_PORT API_TOKEN; do
  find_text "^${key}=" .env.example || { echo "[FAIL] missing $key in .env.example"; exit 1; }
done

echo "[check] docs mention compatibility and target baseline"
find_text 'docker-compose.*v1\.29\.2|docker compose.*v2' README.md
find_text 'Debian 12' README.md
find_text '443.*host Xray|host Xray.*443' README.md

echo "[OK] release-readiness static checks passed"
