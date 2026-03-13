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

if "${COMPOSE[@]}" exec -T api python -c "import urllib.request; urllib.request.urlopen('http://proxy/health', timeout=3)" >/dev/null 2>&1; then
  ok "proxy /health routing"
else
  warn "proxy /health routing"
fi

if "${COMPOSE[@]}" exec -T api python -c "import urllib.request, json; req=urllib.request.Request('http://proxy/api/providers', headers={'x-api-token':'admin-token'}); print(json.loads(urllib.request.urlopen(req, timeout=3).read().decode())['active_provider'])" >/dev/null 2>&1; then
  ok "provider endpoint"
else
  fail "provider endpoint"
fi

if command -v ss >/dev/null 2>&1; then
  if ss -ltn '( sport = :443 )' | grep -q ':443'; then
    ok "host 443 in use (verify ownership policy)"
  else
    warn "host 443 not in use"
  fi
else
  warn "ss command not found, skip host 443 ownership check"
fi

if [[ $status -eq 0 ]]; then
  ok "post-deploy verdict: GREEN"
else
  fail "post-deploy verdict: RED"
fi

exit $status
