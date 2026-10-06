#!/bin/sh
set -eu

# Workstation-side deployment launcher.
# The Synology updater remains the authoritative deployment implementation.
#
# Usage:
#   sh scripts/deploy.sh <ssh-host> [ssh-user]
#
# Optional:
#   PUBLIC_URL=https://rankings.larrybillinger.com
#   SSH_PORT=22

HOST="${1:-${DEPLOY_HOST:-}}"
USER_NAME="${2:-${DEPLOY_USER:-}}"
SSH_PORT="${SSH_PORT:-22}"
PUBLIC_URL="${PUBLIC_URL:-https://rankings.larrybillinger.com}"
REMOTE_UPDATE="/volume1/rankings/app/scripts/synology-update.sh"

if [ -z "$HOST" ]; then
  echo "Usage: sh scripts/deploy.sh <ssh-host> [ssh-user]" >&2
  echo "Or set DEPLOY_HOST and optionally DEPLOY_USER." >&2
  exit 2
fi

TARGET="$HOST"
if [ -n "$USER_NAME" ]; then
  TARGET="$USER_NAME@$HOST"
fi

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
EXPECTED_VERSION=""
if [ -f "$SCRIPT_DIR/../VERSION" ]; then
  EXPECTED_VERSION="$(tr -d '\r\n ' < "$SCRIPT_DIR/../VERSION")"
fi

echo "Deploying D1 Rank${EXPECTED_VERSION:+ v$EXPECTED_VERSION} to $TARGET..."
echo "Remote updater: $REMOTE_UPDATE"
echo

# -t lets sudo request a password when the Synology account is not configured
# for passwordless sudo. The remote updater performs its own source backup,
# downloads main from GitHub, rebuilds the shared image, recreates web/worker,
# and verifies the local /health release/model/predictor identifiers.
ssh -p "$SSH_PORT" -t "$TARGET" "sudo sh '$REMOTE_UPDATE'"

echo
echo "Remote deployment completed."

if command -v curl >/dev/null 2>&1; then
  echo "Checking public HTTPS endpoint: $PUBLIC_URL/health"
  HEALTH="$(curl -fsS --retry 5 --retry-delay 3 --connect-timeout 15 "$PUBLIC_URL/health")"
  printf '%s\n' "$HEALTH"

  if [ -n "$EXPECTED_VERSION" ]; then
    echo "$HEALTH" | grep -q "\"app_version\":\"$EXPECTED_VERSION\"" || {
      echo "ERROR: public endpoint is not reporting app version $EXPECTED_VERSION." >&2
      exit 1
    }
  fi
  echo "Public HTTPS health check passed."
else
  echo "curl is not installed locally; skipped the public HTTPS health check."
  echo "The Synology updater already verified the local application health endpoint."
fi
