#!/bin/sh
set -eu
ROOT="/volume1/rankings"
APP="$ROOT/app"
BACKUPS="$ROOT/backups"
ENV_FILE="$ROOT/.env"
ARCHIVE="https://github.com/larrybillinger/NCAA_BCS_RANKING_CALCULATOR/archive/refs/heads/main.tar.gz"
TMP="/tmp/ncaa-rankings-update-$$"
trap 'rm -rf "$TMP"' EXIT INT TERM

if [ "$(id -u)" -ne 0 ]; then echo "Run as root (sudo -i first)."; exit 1; fi
if [ ! -f "$ENV_FILE" ]; then echo "Missing $ENV_FILE. Run synology-install.sh instead."; exit 1; fi
mkdir -p "$BACKUPS" "$TMP/archive"
STAMP="$(date +%Y%m%d-%H%M%S)"
if [ -d "$APP" ]; then tar -czf "$BACKUPS/app-$STAMP.tar.gz" -C "$ROOT" app; fi

curl -fL --retry 3 "$ARCHIVE" -o "$TMP/source.tar.gz"
tar -xzf "$TMP/source.tar.gz" -C "$TMP/archive"
SOURCE_DIR="$(find "$TMP/archive" -mindepth 1 -maxdepth 1 -type d | head -n 1)"
rm -rf "$APP.new" && mkdir -p "$APP.new"
cp -a "$SOURCE_DIR/." "$APP.new/"
rm -rf "$APP" && mv "$APP.new" "$APP"
cd "$APP"
docker compose --env-file "$ENV_FILE" up -d --build --remove-orphans
docker image prune -f >/dev/null 2>&1 || true
echo "Update complete. Backup: $BACKUPS/app-$STAMP.tar.gz"
