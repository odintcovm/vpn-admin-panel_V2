#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "$0")/common.sh"
service="${1:-}"
if [[ -n "$service" ]]; then
  "${COMPOSE[@]}" logs -f "$service"
else
  "${COMPOSE[@]}" logs -f --tail=200
fi
