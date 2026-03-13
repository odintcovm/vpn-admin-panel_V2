#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "$0")/common.sh"

if [[ -d .git ]]; then
  log_info "Pull latest changes..."
  git pull --ff-only
fi

log_info "Rebuild and start services..."
"${COMPOSE[@]}" up -d --build

log_info "Apply migrations..."
"${COMPOSE[@]}" exec -T api sh -lc 'PYTHONPATH=. alembic upgrade head'

log_info "Restart app services..."
"${COMPOSE[@]}" restart api web proxy
log_info "Update complete"
