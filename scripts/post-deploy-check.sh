#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "$0")/common.sh"

status=0
warn(){ echo "[WARN] $*"; }
fail(){ echo "[FAIL] $*"; status=1; }
ok(){ echo "[OK] $*"; }

"${COMPOSE[@]}" ps || fail "compose ps failed"

if "${COMPOSE[@]}" exec -T api python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=3)" >/dev/null 2>&1; then
  ok "api /health"
else
  fail "api /health"
fi

if "${COMPOSE[@]}" exec -T api python -c "import urllib.request; req=urllib.request.Request('http://proxy/api/auth/me', headers={'x-api-token':'admin-token'}); urllib.request.urlopen(req, timeout=3)" >/dev/null 2>&1; then
  ok "auth endpoint"
else
  warn "auth endpoint failed (maybe non-default API_TOKEN)"
fi

if [[ $status -eq 0 ]]; then
  ok "post-deploy verdict: GREEN"
else
  fail "post-deploy verdict: RED"
fi

exit $status
