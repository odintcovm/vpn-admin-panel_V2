#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "$0")/common.sh"
mkdir -p backups
stamp="$(date +%Y%m%d_%H%M%S)"
out="backups/vpn_admin_backup_${stamp}.tar.gz"
"${COMPOSE[@]}" exec -T api sh -lc 'test -f /app/data/data.db || test -f /app/data.db || exit 1'
"${COMPOSE[@]}" exec -T api sh -lc 'if [ -f /app/data/data.db ]; then cat /app/data/data.db; else cat /app/data.db; fi' > "backups/data_${stamp}.db"
tar -czf "$out" "backups/data_${stamp}.db" docker/xray/config.json .env
rm -f "backups/data_${stamp}.db"
echo "Backup created: $out"
