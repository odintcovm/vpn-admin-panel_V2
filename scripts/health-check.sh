#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "$0")/common.sh"
"${COMPOSE[@]}" ps
if ! "${COMPOSE[@]}" exec -T api python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=3)" >/dev/null; then
  echo "[ERR] API health check failed"
  exit 1
fi
if ! "${COMPOSE[@]}" exec -T proxy sh -lc "wget -q -O- http://127.0.0.1/api/system/health >/dev/null"; then
  echo "[WARN] Proxy check failed (maybe domain-only TLS config)"
fi
echo "Health check OK"
