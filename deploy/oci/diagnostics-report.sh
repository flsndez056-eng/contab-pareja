#!/usr/bin/env sh
set -eu

days="${1:-7}"
case "$days" in
  *[!0-9]*|'') echo "Uso: $0 [días]" >&2; exit 2 ;;
esac
if [ "$days" -lt 1 ] || [ "$days" -gt 30 ]; then
  echo "El rango debe estar entre 1 y 30 días." >&2
  exit 2
fi

docker compose --env-file .env.production -f compose.oci.yaml exec -T postgres \
  psql --username contab --dbname contab_pareja --set ON_ERROR_STOP=1 \
  --command "
    SELECT
      fingerprint,
      error_type,
      app_version,
      COUNT(*) AS occurrences,
      MAX(occurred_at) AS last_seen
    FROM client_error_reports
    WHERE occurred_at >= now() - make_interval(days => $days)
    GROUP BY fingerprint, error_type, app_version
    ORDER BY occurrences DESC, last_seen DESC
    LIMIT 100;
  "
