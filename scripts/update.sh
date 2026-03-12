#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "$0")/common.sh"
if [[ -d .git ]]; then
  git pull --ff-only
fi
"${COMPOSE[@]}" up -d --build
"${COMPOSE[@]}" exec -T api sh -lc 'PYTHONPATH=. alembic upgrade head'
"${COMPOSE[@]}" restart api web proxy
echo "Update complete"
