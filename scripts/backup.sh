#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "$0")/common.sh"

mkdir -p backups
stamp="$(date +%Y%m%d_%H%M%S)"
out="backups/vpn_admin_backup_${stamp}.tar.gz"
tmp_db="backups/data_${stamp}.db"

"${COMPOSE[@]}" exec -T api sh -lc 'test -f /app/data/data.db || test -f /app/data.db || exit 1'
"${COMPOSE[@]}" exec -T api sh -lc 'if [ -f /app/data/data.db ]; then cat /app/data/data.db; else cat /app/data.db; fi' > "$tmp_db"

if [[ ! -f .env ]]; then
  log_warn ".env not found; backup will include only DB and Xray config"
  tar -czf "$out" "$tmp_db" docker/xray/config.json
else
  tar -czf "$out" "$tmp_db" docker/xray/config.json .env
fi

rm -f "$tmp_db"
log_info "Backup created: $out"
