#!/bin/sh
set -eu

# Synology/Container Manager can be slow to export images. Avoid client-side
# timeouts while Docker is still successfully working.
export DOCKER_CLIENT_TIMEOUT="${DOCKER_CLIENT_TIMEOUT:-1200}"
export COMPOSE_HTTP_TIMEOUT="${COMPOSE_HTTP_TIMEOUT:-1200}"

ROOT="/volume1/rankings"
APP="$ROOT/app"
BACKUPS="$ROOT/backups"
ENV_FILE="$ROOT/.env"
ARCHIVE="https://github.com/larrybillinger/NCAA_BCS_RANKING_CALCULATOR/archive/refs/heads/main.tar.gz"
TMP="/tmp/ncaa-rankings-update-$$"
trap 'rm -rf "$TMP"' EXIT INT TERM

if [ "$(id -u)" -ne 0 ]; then
  echo "Run as root (sudo -i first)."
  exit 1
fi
if [ ! -f "$ENV_FILE" ]; then
  echo "Missing $ENV_FILE. Run synology-install.sh instead."
  exit 1
fi
if ! command -v docker >/dev/null 2>&1; then
  echo "Docker was not found. Install/start Synology Container Manager first."
  exit 1
fi

# The updater replaces $APP, so leave it before removing the directory.
cd /

compose() {
  if docker compose version >/dev/null 2>&1; then
    docker compose "$@"
  elif command -v docker-compose >/dev/null 2>&1; then
    docker-compose "$@"
  else
    echo "Neither 'docker compose' nor 'docker-compose' is available." >&2
    return 127
  fi
}

download() {
  url="$1"
  output="$2"
  if command -v curl >/dev/null 2>&1; then
    curl -fL --retry 3 --connect-timeout 20 "$url" -o "$output"
  elif command -v wget >/dev/null 2>&1; then
    wget -O "$output" "$url"
  else
    echo "Neither curl nor wget is available on this NAS." >&2
    return 127
  fi
}

set_env_key() {
  key="$1"
  value="$2"
  tmp_env="$ENV_FILE.tmp.$$"

  awk -v key="$key" -v value="$value" '
    BEGIN { found=0 }
    index($0, key "=") == 1 {
      print key "=" value
      found=1
      next
    }
    { print }
    END {
      if (!found) print key "=" value
    }
  ' "$ENV_FILE" > "$tmp_env"

  chmod 600 "$tmp_env"
  mv "$tmp_env" "$ENV_FILE"
}

mkdir -p "$BACKUPS" "$TMP/archive"
STAMP="$(date +%Y%m%d-%H%M%S)"
if [ -d "$APP" ]; then
  echo "Backing up current application files..."
  tar -czf "$BACKUPS/app-$STAMP.tar.gz" -C "$ROOT" app
fi

echo "Downloading latest source..."
download "$ARCHIVE" "$TMP/source.tar.gz"
tar -xzf "$TMP/source.tar.gz" -C "$TMP/archive"
SOURCE_DIR="$(find "$TMP/archive" -mindepth 1 -maxdepth 1 -type d | head -n 1)"
if [ -z "$SOURCE_DIR" ] || [ ! -f "$SOURCE_DIR/docker-compose.yml" ]; then
  echo "Downloaded archive does not contain the expected application files."
  exit 1
fi

# Application model identifiers are not secrets. Keep production aligned with
# the versions committed in GitHub while preserving passwords/API keys.
if [ -f "$SOURCE_DIR/.env.example" ]; then
  REQUIRED_MODEL="$(awk -F= '/^MODEL_VERSION=/{print $2}' "$SOURCE_DIR/.env.example" | tail -n 1)"
  REQUIRED_PREDICTOR="$(awk -F= '/^PREDICTOR_VERSION=/{print $2}' "$SOURCE_DIR/.env.example" | tail -n 1)"

  if [ -n "$REQUIRED_MODEL" ]; then
    echo "Setting MODEL_VERSION=$REQUIRED_MODEL"
    set_env_key MODEL_VERSION "$REQUIRED_MODEL"
  fi
  if [ -n "$REQUIRED_PREDICTOR" ]; then
    echo "Setting PREDICTOR_VERSION=$REQUIRED_PREDICTOR"
    set_env_key PREDICTOR_VERSION "$REQUIRED_PREDICTOR"
  fi
fi

rm -rf "$APP.new"
mkdir -p "$APP.new"
cp -a "$SOURCE_DIR/." "$APP.new/"
rm -rf "$APP"
mv "$APP.new" "$APP"

cd "$APP"

EXPECTED_APP="$(tr -d '\r\n ' < VERSION)"
EXPECTED_MODEL="$(awk -F= '/^MODEL_VERSION=/{print $2}' "$ENV_FILE" | tail -n 1)"
EXPECTED_PREDICTOR="$(awk -F= '/^PREDICTOR_VERSION=/{print $2}' "$ENV_FILE" | tail -n 1)"

echo "Building shared application image once..."
docker build -t ncaa-rankings-app:latest .

echo "Ensuring PostgreSQL is running..."
compose --env-file "$ENV_FILE" up -d db

echo "Recreating web and worker from the new image..."
compose --env-file "$ENV_FILE" up -d --no-deps --force-recreate web worker
compose --env-file "$ENV_FILE" up -d --remove-orphans

PORT="$(awk -F= '/^WEB_PORT=/{print $2}' "$ENV_FILE" | tail -n 1)"
PORT="${PORT:-8765}"

echo "Waiting for the updated website to become healthy..."
ATTEMPT=0
while :; do
  if command -v curl >/dev/null 2>&1; then
    if curl -fsS "http://127.0.0.1:$PORT/health" >/tmp/rankings-health.json 2>/dev/null; then
      break
    fi
  elif command -v wget >/dev/null 2>&1; then
    if wget -q -O /tmp/rankings-health.json "http://127.0.0.1:$PORT/health"; then
      break
    fi
  fi

  ATTEMPT=$((ATTEMPT + 1))
  if [ "$ATTEMPT" -ge 45 ]; then
    echo "ERROR: updated website did not become healthy in time."
    docker logs --tail 160 ncaa-rankings-web || true
    docker logs --tail 100 ncaa-rankings-worker || true
    exit 1
  fi
  sleep 4
done

HEALTH="$(cat /tmp/rankings-health.json)"
echo "$HEALTH" | grep -q "\"app_version\":\"$EXPECTED_APP\"" || {
  echo "ERROR: running app version does not match GitHub ($EXPECTED_APP)."
  echo "$HEALTH"
  exit 1
}
echo "$HEALTH" | grep -q "\"model_version\":\"$EXPECTED_MODEL\"" || {
  echo "ERROR: running model does not match GitHub ($EXPECTED_MODEL)."
  echo "$HEALTH"
  exit 1
}
echo "$HEALTH" | grep -q "\"predictor_version\":\"$EXPECTED_PREDICTOR\"" || {
  echo "ERROR: running predictor does not match GitHub ($EXPECTED_PREDICTOR)."
  echo "$HEALTH"
  exit 1
}

docker image prune -f >/dev/null 2>&1 || true

echo
echo "Update complete."
echo "Backup: $BACKUPS/app-$STAMP.tar.gz"
echo
echo "Verified active release:"
echo "$HEALTH"
echo
echo "Container status:"
compose --env-file "$ENV_FILE" ps || true
