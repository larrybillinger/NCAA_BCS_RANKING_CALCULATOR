#!/bin/sh
set -eu

REPO_ARCHIVE="https://github.com/larrybillinger/NCAA_BCS_RANKING_CALCULATOR/archive/refs/heads/main.tar.gz"
ROOT="/volume1/rankings"
APP="$ROOT/app"
BACKUPS="$ROOT/backups"
ENV_FILE="$ROOT/.env"
WEB_PORT_DEFAULT="8765"
SEASON_DEFAULT="2026"
TMP="/tmp/ncaa-rankings-install-$$"

cleanup() { rm -rf "$TMP"; }
trap cleanup EXIT INT TERM

if [ "$(id -u)" -ne 0 ]; then
  echo "Run this installer as root (sudo -i first)."
  exit 1
fi
if ! command -v docker >/dev/null 2>&1; then
  echo "Docker was not found. Install Synology Container Manager first."
  exit 1
fi

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

health_ok() {
  url="$1"
  if command -v curl >/dev/null 2>&1; then
    curl -fsS "$url" >/dev/null 2>&1
  elif command -v wget >/dev/null 2>&1; then
    wget -q -O /dev/null "$url" >/dev/null 2>&1
  else
    return 1
  fi
}

# Fail early if no Compose implementation is available.
compose version >/dev/null 2>&1 || {
  echo "Docker Compose is not available. Update/install Synology Container Manager."
  exit 1
}

mkdir -p "$ROOT" "$BACKUPS" "$ROOT/postgres" "$TMP"

if [ -d "$APP" ]; then
  STAMP="$(date +%Y%m%d-%H%M%S)"
  echo "Backing up current application files to $BACKUPS/app-$STAMP.tar.gz"
  tar -czf "$BACKUPS/app-$STAMP.tar.gz" -C "$ROOT" app
fi

if [ -f "$ENV_FILE" ]; then
  echo "Existing $ENV_FILE will be preserved."
else
  printf "CollegeFootballData API key (leave blank to install without automatic sync): "
  read -r CFBD_KEY || CFBD_KEY=""
  printf "Web port [%s]: " "$WEB_PORT_DEFAULT"
  read -r WEB_PORT || WEB_PORT=""
  WEB_PORT="${WEB_PORT:-$WEB_PORT_DEFAULT}"
  printf "Season [%s]: " "$SEASON_DEFAULT"
  read -r SEASON || SEASON=""
  SEASON="${SEASON:-$SEASON_DEFAULT}"

  if command -v openssl >/dev/null 2>&1; then
    DB_PASSWORD="$(openssl rand -hex 24)"
  else
    DB_PASSWORD="rankings-$(date +%s)-$$"
  fi

  cat > "$ENV_FILE" <<EOF
POSTGRES_DB=rankings
POSTGRES_USER=rankings
POSTGRES_PASSWORD=$DB_PASSWORD
DATABASE_URL=postgresql+psycopg://rankings:$DB_PASSWORD@db:5432/rankings
WEB_PORT=$WEB_PORT
WEB_TITLE=D1 Rank
TZ=America/Chicago
SEASON=$SEASON
BOOTSTRAP_RANKINGS=true
MODEL_VERSION=division_i_weighted_v1
PREDICTOR_VERSION=rank_gap_v1
CFBD_API_KEY=$CFBD_KEY
CFBD_BASE_URL=https://api.collegefootballdata.com
SYNC_MINUTES=15
EOF
  chmod 600 "$ENV_FILE"
fi

mkdir -p "$TMP/archive"
echo "Downloading latest NCAA ranking site source..."
download "$REPO_ARCHIVE" "$TMP/source.tar.gz"

tar -xzf "$TMP/source.tar.gz" -C "$TMP/archive"
SOURCE_DIR="$(find "$TMP/archive" -mindepth 1 -maxdepth 1 -type d | head -n 1)"
if [ -z "$SOURCE_DIR" ] || [ ! -f "$SOURCE_DIR/docker-compose.yml" ]; then
  echo "Downloaded archive does not contain the expected application files."
  exit 1
fi

rm -rf "$APP.new"
mkdir -p "$APP.new"
cp -a "$SOURCE_DIR/." "$APP.new/"
rm -rf "$APP"
mv "$APP.new" "$APP"

cd "$APP"
echo "Building and starting containers..."
compose --env-file "$ENV_FILE" up -d --build --remove-orphans

echo "Waiting for the web application to become healthy..."
PORT="$(awk -F= '/^WEB_PORT=/{print $2}' "$ENV_FILE" | tail -n 1)"
PORT="${PORT:-$WEB_PORT_DEFAULT}"
ATTEMPT=0
until health_ok "http://127.0.0.1:$PORT/health"; do
  ATTEMPT=$((ATTEMPT + 1))
  if [ "$ATTEMPT" -ge 30 ]; then
    echo "The site did not become healthy in time. Recent logs:"
    compose --env-file "$ENV_FILE" logs --tail=80 web worker db || true
    exit 1
  fi
  sleep 4
done

echo
echo "D1 Rank is running."
HOST_IP="$(hostname -I 2>/dev/null | awk '{print $1}')"
echo "Local URL: http://${HOST_IP:-YOUR-SYNOLOGY-IP}:$PORT"
echo "App folder: $APP"
echo "PostgreSQL data: $ROOT/postgres"
echo "Environment/secrets: $ENV_FILE"
echo
echo "Useful commands:"
echo "  cd $APP"
echo "  docker logs --tail 200 ncaa-rankings-web"
echo "  docker logs --tail 200 ncaa-rankings-worker"
echo
echo "To update later:"
echo "  sudo sh $APP/scripts/synology-update.sh"
