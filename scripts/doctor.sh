#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

MODE="${1:-prod-like}"
status=0

green(){ echo "[GREEN] $*"; }
yellow(){ echo "[YELLOW] $*"; }
red(){ echo "[RED] $*"; status=1; }

[[ -f .env ]] || cp .env.example .env

if command -v docker >/dev/null 2>&1; then green "docker installed"; else red "docker missing"; fi
if docker compose version >/dev/null 2>&1 || command -v docker-compose >/dev/null 2>&1; then green "compose available"; else red "compose missing"; fi

if command -v ss >/dev/null 2>&1; then
  if ss -ltn '( sport = :443 )' | grep -q ':443'; then
    yellow "host 443 busy (safe when host Xray owns dataplane)"
  else
    green "host 443 free"
  fi
else
  yellow "ss command not found, skip 443 ownership check"
fi

if [[ -f /etc/debian_version ]]; then
  if grep -q '^12' /etc/debian_version; then
    green "Debian 12 detected"
  else
    yellow "Target baseline is Debian 12; detected $(cat /etc/debian_version)"
  fi
else
  yellow "Cannot verify Debian version"
fi

mem_mb="$(awk '/MemTotal/ {print int($2/1024)}' /proc/meminfo 2>/dev/null || echo 0)"
if [[ "$mem_mb" -lt 1800 ]]; then
  red "RAM below recommended minimum 2GB (${mem_mb}MB detected)"
else
  green "RAM check ok (${mem_mb}MB)"
fi

for key in APP_PROVIDER APP_ENV SCHEMA_MANAGEMENT_MODE ENABLE_TLS_PROXY ENABLE_XRAY_PUBLIC API_TOKEN; do
  if grep -q "^${key}=" .env; then green ".env has ${key}"; else red ".env missing ${key}"; fi
done

provider="$(grep -E '^APP_PROVIDER=' .env | tail -n1 | cut -d= -f2-)"
if [[ "$provider" =~ ^(xray|avg|wg|mock)$ ]]; then
  green "provider '${provider}' is accepted"
else
  red "unsupported provider '${provider}'"
fi

if [[ "$(grep -E '^API_TOKEN=' .env | tail -n1 | cut -d= -f2-)" == "admin-token" ]]; then
  yellow "API_TOKEN is default admin-token; rotate for production"
fi

if [[ "$status" -eq 0 ]]; then
  green "doctor verdict: GREEN"
else
  red "doctor verdict: RED"
fi

exit $status
