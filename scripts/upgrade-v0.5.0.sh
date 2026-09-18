#!/bin/sh
set -eu

ROOT="/volume1/rankings"
APP="$ROOT/app"
ENV_FILE="$ROOT/.env"
BACKUPS="$ROOT/backups"
ARCHIVE="https://github.com/larrybillinger/NCAA_BCS_RANKING_CALCULATOR/archive/refs/heads/main.tar.gz"
TMP="/tmp/ncaa-rankings-v050-$$"
STAMP="$(date +%Y%m%d-%H%M%S)"

cleanup() {
  rm -rf "$TMP"
}
trap cleanup EXIT INT TERM

if [ "$(id -u)" -ne 0 ]; then
  echo "Run as root first: sudo -i"
  exit 1
fi

if [ ! -f "$ENV_FILE" ]; then
  echo "Missing $ENV_FILE"
  exit 1
fi

compose() {
  if docker compose version >/dev/null 2>&1; then
    docker compose "$@"
  elif command -v docker-compose >/dev/null 2>&1; then
    docker-compose "$@"
  else
    echo "Neither docker compose nor docker-compose is available." >&2
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
    echo "Neither curl nor wget is available." >&2
    return 127
  fi
}

health_ok() {
  url="$1"
  if command -v curl >/dev/null 2>&1; then
    curl -fsS "$url" >/dev/null 2>&1
  else
    wget -q -O /dev/null "$url" >/dev/null 2>&1
  fi
}

http_code() {
  url="$1"
  if command -v curl >/dev/null 2>&1; then
    curl -sS -o /dev/null -w '%{http_code}' "$url" || true
  else
    if wget -q -O /dev/null "$url"; then
      echo 200
    else
      echo 000
    fi
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

echo "============================================================"
echo " D1 Rank v0.5.0 upgrade"
echo " Neutral T-1 Week 1 baseline + averaged tie scoring ranks"
echo "============================================================"
echo

mkdir -p "$BACKUPS" "$TMP/archive"

echo "1/7 Backing up application and environment..."
if [ -d "$APP" ]; then
  tar -czf "$BACKUPS/app-env-$STAMP.tar.gz" -C "$ROOT" app .env
  chmod 600 "$BACKUPS/app-env-$STAMP.tar.gz"
fi

echo "2/7 Backing up PostgreSQL..."
if docker ps --format '{{.Names}}' | grep -qx 'ncaa-rankings-db'; then
  if docker exec ncaa-rankings-db sh -c 'pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB"' \
      | gzip > "$BACKUPS/postgres-$STAMP.sql.gz"; then
    chmod 600 "$BACKUPS/postgres-$STAMP.sql.gz"
    echo "Database backup: $BACKUPS/postgres-$STAMP.sql.gz"
  else
    rm -f "$BACKUPS/postgres-$STAMP.sql.gz"
    echo "WARNING: PostgreSQL backup failed. Application backup still exists."
  fi
else
  echo "WARNING: ncaa-rankings-db is not currently running; skipping database dump."
fi

echo "3/7 Downloading v0.5.0 source..."
download "$ARCHIVE" "$TMP/source.tar.gz"
tar -xzf "$TMP/source.tar.gz" -C "$TMP/archive"
SOURCE_DIR="$(find "$TMP/archive" -mindepth 1 -maxdepth 1 -type d | head -n 1)"
if [ -z "$SOURCE_DIR" ] || [ ! -f "$SOURCE_DIR/docker-compose.yml" ]; then
  echo "Downloaded archive does not contain the expected application."
  exit 1
fi

echo "4/7 Switching production model versions..."
set_env_key MODEL_VERSION division_i_weighted_v2
set_env_key PREDICTOR_VERSION rank_gap_v2

echo "5/7 Preparing PostgreSQL for fractional tied ranks..."
if docker ps --format '{{.Names}}' | grep -qx 'ncaa-rankings-db'; then
  docker exec ncaa-rankings-db psql -U rankings -d rankings -v ON_ERROR_STOP=1 -c \
    "ALTER TABLE ranking_game_audits
     ALTER COLUMN opponent_rank_used TYPE DOUBLE PRECISION
     USING opponent_rank_used::double precision;" >/dev/null
fi

echo "6/7 Installing source and rebuilding containers..."
rm -rf "$APP.new"
mkdir -p "$APP.new"
cp -a "$SOURCE_DIR/." "$APP.new/"
rm -rf "$APP"
mv "$APP.new" "$APP"

cd "$APP"
compose --env-file "$ENV_FILE" up -d --build --remove-orphans

PORT="$(awk -F= '/^WEB_PORT=/{print $2}' "$ENV_FILE" | tail -n 1)"
PORT="${PORT:-8765}"

echo "Waiting for the web application..."
ATTEMPT=0
until health_ok "http://127.0.0.1:$PORT/health"; do
  ATTEMPT=$((ATTEMPT + 1))
  if [ "$ATTEMPT" -ge 45 ]; then
    echo
    echo "ERROR: health endpoint did not become ready."
    docker logs --tail 120 ncaa-rankings-web || true
    docker logs --tail 80 ncaa-rankings-worker || true
    exit 1
  fi
  sleep 4
done

echo "7/7 Verifying rankings page and v2 snapshots..."
HOME_CODE="$(http_code "http://127.0.0.1:$PORT/")"
if [ "$HOME_CODE" != "200" ]; then
  echo "ERROR: homepage returned HTTP $HOME_CODE"
  docker logs --tail 160 ncaa-rankings-web || true
  exit 1
fi

echo
echo "Active model:"
grep '^MODEL_VERSION=' "$ENV_FILE"
grep '^PREDICTOR_VERSION=' "$ENV_FILE"
echo
echo "Health:"
if command -v curl >/dev/null 2>&1; then
  curl -fsS "http://127.0.0.1:$PORT/health"
  echo
fi

echo
echo "Bundled v2 snapshots:"
docker exec ncaa-rankings-db psql -U rankings -d rankings -P pager=off -c "
SELECT season, week, model_version, COUNT(re.id) AS teams
FROM ranking_snapshots rs
LEFT JOIN ranking_entries re ON re.snapshot_id = rs.id
WHERE rs.model_version = 'division_i_weighted_v2'
  AND rs.official IS TRUE
GROUP BY rs.id, season, week, model_version
ORDER BY week;
"

echo
echo "Kansas State / Tulane Week 2 check:"
docker exec ncaa-rankings-db psql -U rankings -d rankings -P pager=off -c "
SELECT re.rank, t.name, re.wins || '-' || re.losses AS record, re.score
FROM ranking_entries re
JOIN ranking_snapshots rs ON rs.id = re.snapshot_id
JOIN teams t ON t.id = re.team_id
WHERE rs.season = 2026
  AND rs.week = 2
  AND rs.model_version = 'division_i_weighted_v2'
  AND rs.official IS TRUE
  AND t.name IN ('Kansas State', 'Tulane')
ORDER BY re.rank;
"

echo
echo "============================================================"
echo " Upgrade complete."
echo " Local site: http://127.0.0.1:$PORT/"
echo " Public site: https://rankings.larrybillinger.com"
echo " Backup stamp: $STAMP"
echo "============================================================"
