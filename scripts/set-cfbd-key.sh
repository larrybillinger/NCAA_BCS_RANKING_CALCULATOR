#!/bin/sh
set -eu

ROOT="/volume1/rankings"
ENV_FILE="$ROOT/.env"
APP="$ROOT/app"

if [ "$(id -u)" -ne 0 ]; then
  echo "Run as root first: sudo -i"
  exit 1
fi

if [ ! -f "$ENV_FILE" ]; then
  echo "Missing $ENV_FILE"
  exit 1
fi

printf "Paste your CollegeFootballData API key: "
stty -echo 2>/dev/null || true
IFS= read -r KEY
stty echo 2>/dev/null || true
printf "\n"

if [ -z "$KEY" ]; then
  echo "No key entered; nothing changed."
  exit 1
fi

case "$KEY" in
  github_pat_*|ghp_*|gho_*|ghu_*|ghs_*|ghr_*)
    echo "That looks like a GitHub token, not a CollegeFootballData API key."
    echo "Get a CFBD key from https://collegefootballdata.com/key"
    exit 1
    ;;
esac

echo "Testing CFBD key..."
STATUS="$(curl -sS -o /tmp/cfbd-key-test.json -w '%{http_code}' \
  --get 'https://api.collegefootballdata.com/games' \
  --data-urlencode 'year=2026' \
  --data-urlencode 'week=3' \
  --data-urlencode 'seasonType=regular' \
  --data-urlencode 'classification=fbs' \
  --header "Authorization: Bearer $KEY" || true)"

if [ "$STATUS" != "200" ]; then
  echo "CFBD rejected the key. HTTP status: $STATUS"
  echo "Response:"
  head -c 500 /tmp/cfbd-key-test.json 2>/dev/null || true
  echo
  exit 1
fi

TMP_ENV="$ENV_FILE.tmp.$$"
awk -v key="$KEY" '
BEGIN { found=0 }
$0 ~ /^CFBD_API_KEY=/ {
  print "CFBD_API_KEY=" key
  found=1
  next
}
{ print }
END {
  if (!found) print "CFBD_API_KEY=" key
}
' "$ENV_FILE" > "$TMP_ENV"

chmod 600 "$TMP_ENV"
mv "$TMP_ENV" "$ENV_FILE"

cd "$APP"

if docker compose version >/dev/null 2>&1; then
  docker compose --env-file "$ENV_FILE" up -d --force-recreate worker web
elif command -v docker-compose >/dev/null 2>&1; then
  docker-compose --env-file "$ENV_FILE" up -d --force-recreate worker web
else
  echo "Docker Compose was not found."
  exit 1
fi

echo
echo "CFBD key accepted and saved."
echo "Worker and web containers recreated."
echo
echo "Current health:"
curl -fsS http://127.0.0.1:8765/health || true
echo
