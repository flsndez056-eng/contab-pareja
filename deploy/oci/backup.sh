#!/usr/bin/env sh
set -eu
umask 077

backup_dir="${BACKUP_DIR:-./backups}"
timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
backup_file="$backup_dir/contab-pareja-$timestamp.dump"
mkdir -p "$backup_dir"

trap 'rm -f "$backup_file"' HUP INT TERM EXIT
docker compose --env-file .env.production -f compose.oci.yaml exec -T postgres \
  pg_dump --username contab --dbname contab_pareja --format=custom \
  > "$backup_file"
trap - HUP INT TERM EXIT

find "$backup_dir" -type f -name 'contab-pareja-*.dump' -mtime +14 -delete
