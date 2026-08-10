#!/usr/bin/env sh
set -eu
umask 077

backup_dir="${BACKUP_DIR:-./backups}"
backup_file="${1:-}"
if [ -z "$backup_file" ]; then
  backup_file="$(find "$backup_dir" -type f -name 'contab-pareja-*.dump' | sort | tail -n 1)"
fi
if [ -z "$backup_file" ] || [ ! -f "$backup_file" ]; then
  echo "No se encontró un respaldo para verificar." >&2
  exit 1
fi

checksum_file="$backup_file.sha256"
if [ ! -f "$checksum_file" ]; then
  echo "Falta el checksum: $checksum_file" >&2
  exit 1
fi

(
  cd "$(dirname "$backup_file")"
  sha256sum --check "$(basename "$checksum_file")"
)

compose() {
  docker compose --env-file .env.production -f compose.oci.yaml "$@"
}

compose exec -T postgres pg_restore --list < "$backup_file" > /dev/null
verify_db="contab_verify_$(date -u +%Y%m%d%H%M%S)_$$"
cleanup() {
  compose exec -T postgres dropdb --username contab --if-exists "$verify_db" > /dev/null 2>&1 || true
}
trap cleanup HUP INT TERM EXIT

compose exec -T postgres createdb --username contab "$verify_db"
compose exec -T postgres pg_restore \
  --username contab --dbname "$verify_db" --no-owner --no-privileges < "$backup_file"
compose exec -T postgres psql --username contab --dbname "$verify_db" \
  --set ON_ERROR_STOP=1 --tuples-only \
  --command "SELECT COUNT(*) FROM alembic_version; SELECT COUNT(*) FROM users; SELECT COUNT(*) FROM expense_requests;" \
  > /dev/null

cleanup
trap - HUP INT TERM EXIT
verified_at="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
marker="$backup_dir/last-verified.txt"
printf '%s %s\n' "$verified_at" "$(basename "$backup_file")" > "$marker.tmp"
mv "$marker.tmp" "$marker"
printf 'Respaldo verificado mediante restauración: %s\n' "$backup_file"
