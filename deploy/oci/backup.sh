#!/usr/bin/env sh
set -eu
umask 077

backup_dir="${BACKUP_DIR:-./backups}"
timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
backup_file="$backup_dir/contab-pareja-$timestamp.dump"
partial_file="$backup_file.partial"
mkdir -p "$backup_dir"

trap 'rm -f "$partial_file"' HUP INT TERM EXIT
docker compose --env-file .env.production -f compose.oci.yaml exec -T postgres \
  pg_dump --username contab --dbname contab_pareja --format=custom \
  > "$partial_file"

docker compose --env-file .env.production -f compose.oci.yaml exec -T postgres \
  pg_restore --list < "$partial_file" > /dev/null
mv "$partial_file" "$backup_file"
(
  cd "$backup_dir"
  sha256sum "$(basename "$backup_file")" > "$(basename "$backup_file").sha256"
)
trap - HUP INT TERM EXIT

find "$backup_dir" -type f -name 'contab-pareja-*.dump' -mtime +14 -delete
find "$backup_dir" -type f -name 'contab-pareja-*.dump.sha256' -mtime +14 -delete

printf '%s\n' "$backup_file"
