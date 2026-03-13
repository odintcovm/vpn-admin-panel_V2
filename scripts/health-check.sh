#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "$0")/common.sh"
"${COMPOSE[@]}" ps
if ! "${COMPOSE[@]}" exec -T api python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=3)" >/dev/null; then
  echo "[ERR] API container health check failed"
  exit 1
fi
if ! "${COMPOSE[@]}" exec -T proxy sh -lc "wget -q -O- http://127.0.0.1/health >/dev/null"; then
  echo "[WARN] Proxy /health check failed"
fi
if ! "${COMPOSE[@]}" exec -T proxy sh -lc "wget -q -O- http://127.0.0.1/api/auth/me --header='x-api-token: admin-token' >/dev/null"; then
  echo "[WARN] Proxy /api/auth/me check failed"
fi
echo "Health check OK"
