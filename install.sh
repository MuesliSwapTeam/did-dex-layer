#!/usr/bin/env bash
# Deterministic local setup for the DID DEX Layer project.

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_ROOT"

PYTHON_BIN="${PYTHON_BIN:-python3.11}"
NODE_BIN="${NODE_BIN:-node}"
NPM_BIN="${NPM_BIN:-npm}"

require_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "ERROR: '$1' is required but was not found on PATH." >&2
    exit 1
  fi
}

require_cmd "$PYTHON_BIN"
require_cmd "$NODE_BIN"
require_cmd "$NPM_BIN"

PY_VERSION="$("$PYTHON_BIN" - <<'PY'
import sys
print(f"{sys.version_info.major}.{sys.version_info.minor}")
PY
)"

case "$PY_VERSION" in
  3.9|3.10|3.11) ;;
  *)
    echo "ERROR: Python 3.9, 3.10, or 3.11 is required; found $PY_VERSION." >&2
    exit 1
    ;;
esac

NODE_MAJOR="$("$NODE_BIN" -p 'process.versions.node.split(".")[0]')"
if [ "$NODE_MAJOR" -lt 18 ]; then
  echo "ERROR: Node.js 18+ is required; found $("$NODE_BIN" --version)." >&2
  exit 1
fi

echo "==> Installing Python runtime environment (.venv311)"
"$PYTHON_BIN" -m venv .venv311
.venv311/bin/python -m pip install --upgrade pip
.venv311/bin/python -m pip install \
  "cbor2<6" "pycardano>=0.19,<0.20" "fastapi>=0.101,<0.102" "uvicorn[standard]" \
  fastapi-cache2 slowapi peewee==3.17.0 pyjwt==2.8.0 cryptography==36.0.2 \
  pytest pytest-asyncio pytest-cov flask flask-cors ogmios fire blockfrost-python \
  "aiohttp[speedups]" async-lru gelidum orjson psutil click
.venv311/bin/python -m pip install --no-deps "opshin==0.19.1"
.venv311/bin/python -c "import pycardano, fastapi, uvicorn, pytest, ogmios, opshin; print('runtime OK')"

echo "==> Installing OpShin compiler environment (.venv_opshin)"
"$PYTHON_BIN" -m venv .venv_opshin
.venv_opshin/bin/python -m pip install --upgrade pip
.venv_opshin/bin/python -m pip install vendor/pycardano-0.9.0-py3-none-any.whl
.venv_opshin/bin/python -m pip install "opshin==0.19.1" fire
.venv_opshin/bin/python -c "import pycardano, opshin, fire; print('compiler OK')"

echo "==> Installing Node packages"
(cd src/did_dex_frontend && "$NPM_BIN" ci)
(cd src/auth_nft_minting_tool/frontend && "$NPM_BIN" ci)
(cd src/auth_nft_minting_tool && "$NPM_BIN" ci)
(cd src/auth_nft_minting_tool/server && "$NPM_BIN" ci)

echo "==> Installation complete"
echo "Run './scripts/verify_offline.sh' to execute all checks that do not require a running Cardano node."
