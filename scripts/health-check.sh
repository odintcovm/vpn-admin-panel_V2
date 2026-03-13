#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "$0")/common.sh"

"${COMPOSE[@]}" ps

if ! "${COMPOSE[@]}" exec -T api python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=3)" >/dev/null; then
  log_err "API container health check failed"
  exit 1
fi

if ! "${COMPOSE[@]}" exec -T api python -c "import urllib.request; urllib.request.urlopen('http://proxy/health', timeout=3)" >/dev/null; then
  log_warn "Proxy /health route check failed"
fi

if ! "${COMPOSE[@]}" exec -T api python -c "import urllib.request; req=urllib.request.Request('http://proxy/api/auth/me', headers={'x-api-token':'admin-token'}); urllib.request.urlopen(req, timeout=3)" >/dev/null; then
  log_warn "Proxy /api/auth/me route check failed"
fi

if command -v ss >/dev/null 2>&1; then
  if ss -ltn '( sport = :443 )' | grep -q ':443'; then
    log_info "Port 443 is in use on host (expected when host Xray owns dataplane)."
  else
    log_warn "Port 443 appears free on host. Validate intended ingress ownership."
  fi
else
  log_warn "ss command not found, skip 443 ownership check."
fi

log_info "Health check completed"
