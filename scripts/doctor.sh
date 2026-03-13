#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

MODE="${1:-safe}"
status=0

green(){ echo "[GREEN] $*"; }
yellow(){ echo "[YELLOW] $*"; }
red(){ echo "[RED] $*"; status=1; }

[[ -f .env ]] || cp .env.example .env

if command -v docker >/dev/null 2>&1; then green "docker installed"; else red "docker missing"; fi
if docker compose version >/dev/null 2>&1 || command -v docker-compose >/dev/null 2>&1; then green "compose available"; else red "compose missing"; fi

if command -v ss >/dev/null 2>&1; then
  if [[ "$MODE" == "full" ]]; then
    if ss -ltn '( sport = :443 )' | grep -q ':443'; then
      red "port 443 is busy, full mode blocked"
    else
      green "port 443 is free for full mode"
    fi
  else
    if ss -ltn '( sport = :443 )' | grep -q ':443'; then
      yellow "port 443 busy (safe/behind-ingress expected on host with existing ingress)"
    else
      green "port 443 free"
    fi
  fi
else
  yellow "ss command not found, skip port ownership check"
fi

for key in APP_PROVIDER DEPLOY_MODE AUTH_ENABLED ADMIN_USERNAME ENABLE_TLS_PROXY ENABLE_XRAY_PUBLIC; do
  if grep -q "^${key}=" .env; then green ".env has ${key}"; else red ".env missing ${key}"; fi
done

provider="$(grep -E '^APP_PROVIDER=' .env | tail -n1 | cut -d= -f2-)"
if [[ "$provider" =~ ^(xray|wg|avg|mock)$ ]]; then
  green "provider '${provider}' is supported"
else
  red "unsupported provider '${provider}'"
fi

domain="$(grep -E '^DOMAIN=' .env | tail -n1 | cut -d= -f2-)"
enable_tls="$(grep -E '^ENABLE_TLS_PROXY=' .env | tail -n1 | cut -d= -f2-)"
if [[ "$MODE" == "full" && -z "$domain" ]]; then
  red "full mode requires DOMAIN"
fi
if [[ "$enable_tls" == "true" && -z "$domain" ]]; then
  yellow "ENABLE_TLS_PROXY=true but DOMAIN is empty"
fi

if [[ $status -eq 0 ]]; then
  green "doctor verdict: GREEN"
else
  red "doctor verdict: RED"
fi

exit $status
