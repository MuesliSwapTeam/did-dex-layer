#!/usr/bin/env bash
set -euo pipefail

REMOTE_USER="muesliswap"
REMOTE_HOST="preprod.did-dex.muesliswap.com"
REMOTE_DIR="/var/www/preprod.did-dex.muesliswap.com/"
BUILD_DIR="dist"

cd "$(dirname "${BASH_SOURCE[0]}")/.."

if ! command -v rsync >/dev/null 2>&1; then
  echo "rsync is required for deployment." >&2
  exit 1
fi

npm run build

rsync -az --delete "${BUILD_DIR}/" "${REMOTE_USER}@${REMOTE_HOST}:${REMOTE_DIR}"

echo "Deployed ${BUILD_DIR}/ to ${REMOTE_USER}@${REMOTE_HOST}:${REMOTE_DIR}"
