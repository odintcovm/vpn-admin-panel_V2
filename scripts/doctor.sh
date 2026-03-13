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

if [[ ! "$MODE" =~ ^(dev|stage|prod-like)$ ]]; then
  red "mode must be dev|stage|prod-like"
fi

if command -v docker >/dev/null 2>&1; then green "docker installed"; else red "docker missing"; fi
if docker compose version >/dev/null 2>&1 || command -v docker-compose >/dev/null 2>&1; then green "compose available"; else red "compose missing"; fi

if command -v ss >/dev/null 2>&1; then
  if ss -ltn '( sport = :443 )' | grep -q ':443'; then
    yellow "host 443 busy (OK for baseline coexistence with host Xray)"
  else
    green "host 443 free"
  fi
else
  yellow "ss command not found, skip host 443 ownership check"
fi

for key in APP_ENV SCHEMA_MANAGEMENT_MODE APP_PROVIDER ENABLE_TLS_PROXY ENABLE_XRAY_PUBLIC API_TOKEN; do
  if grep -q "^${key}=" .env; then green ".env has ${key}"; else red ".env missing ${key}"; fi
done

provider="$(grep -E '^APP_PROVIDER=' .env | tail -n1 | cut -d= -f2-)"
if [[ "$provider" == "xray" || "$provider" == "mock" ]]; then
  green "provider '${provider}' is supported in this baseline"
else
  yellow "provider '${provider}' is not an official baseline mode (recommended: xray|mock)"
fi

env_mode="$(grep -E '^APP_ENV=' .env | tail -n1 | cut -d= -f2-)"
expected_env="production"
if [[ "$MODE" == "dev" ]]; then expected_env="development"; fi
if [[ "$MODE" == "stage" ]]; then expected_env="staging"; fi
if [[ -n "$env_mode" && "$env_mode" != "$expected_env" ]]; then
  yellow "APP_ENV='${env_mode}', but selected mode '${MODE}' expects '${expected_env}'"
fi

api_token="$(grep -E '^API_TOKEN=' .env | tail -n1 | cut -d= -f2-)"
if [[ "$api_token" == "admin-token" ]]; then
  yellow "API_TOKEN is default admin-token; rotate before internet exposure"
fi

domain="$(grep -E '^DOMAIN=' .env | tail -n1 | cut -d= -f2-)"
enable_tls="$(grep -E '^ENABLE_TLS_PROXY=' .env | tail -n1 | cut -d= -f2-)"
if [[ "$enable_tls" == "true" && -z "$domain" ]]; then
  red "ENABLE_TLS_PROXY=true requires DOMAIN"
fi

if [[ $status -eq 0 ]]; then
  green "doctor verdict: GREEN"
else
  red "doctor verdict: RED"
fi

exit $status
