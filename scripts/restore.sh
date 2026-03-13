#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "$0")/common.sh"

file="${1:-}"
if [[ -z "$file" || ! -f "$file" ]]; then
  echo "Usage: ./scripts/restore.sh <backup.tar.gz>"
  exit 1
fi

tmp_dir="$(mktemp -d)"
cleanup() { rm -rf "$tmp_dir"; }
trap cleanup EXIT

tar -xzf "$file" -C "$tmp_dir"

if [[ -f "$tmp_dir/.env" ]]; then cp "$tmp_dir/.env" .env; fi
if [[ -f "$tmp_dir/docker/xray/config.json" ]]; then cp "$tmp_dir/docker/xray/config.json" docker/xray/config.json; fi

db_file="$(find "$tmp_dir" -name 'data_*.db' | head -n1 || true)"
if [[ -n "$db_file" ]]; then
  "${COMPOSE[@]}" up -d api
  cat "$db_file" | "${COMPOSE[@]}" exec -T api sh -lc 'mkdir -p /app/data && cat > /app/data/data.db'
else
  log_warn "No DB file in backup archive"
fi

"${COMPOSE[@]}" restart api web proxy

log_info "Restore complete. Run ./scripts/health-check.sh"
