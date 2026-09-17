#!/bin/sh
set -eu
ROOT="/volume1/rankings"
APP="$ROOT/app"
ENV_FILE="$ROOT/.env"
BACKUPS="$ROOT/backups"
STAMP="$(date +%Y%m%d-%H%M%S)"
mkdir -p "$BACKUPS"
cd "$APP"

docker compose --env-file "$ENV_FILE" exec -T db sh -c 'pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB"' | gzip > "$BACKUPS/postgres-$STAMP.sql.gz"
tar -czf "$BACKUPS/app-$STAMP.tar.gz" -C "$ROOT" app .env
echo "Backup complete: $STAMP"
