#!/usr/bin/env bash
# Run all reproducible checks that do not require private keys, funded wallets,
# Ogmios, Blockfrost availability, or a running Cardano node.

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

require_file() {
  if [ ! -e "$1" ]; then
    echo "ERROR: missing $1. Run './install.sh' first." >&2
    exit 1
  fi
}

require_file .venv311/bin/python
require_file .venv_opshin/bin/opshin
require_file src/did_dex_frontend/node_modules
require_file src/auth_nft_minting_tool/frontend/node_modules

echo "==> Python tests"
PYTHONPATH=src .venv311/bin/python -m pytest src/tests/

echo "==> OpShin compiler checks"
CONTRACT_OUT="$(mktemp -d "${TMPDIR:-/tmp}/did-dex-contracts.XXXXXX")"
PYTHONPATH=src .venv_opshin/bin/opshin build spending src/orderbook/on_chain/orderbook.py --recursion-limit 3000 -o "$CONTRACT_OUT/orderbook"
PYTHONPATH=src .venv_opshin/bin/opshin build minting src/orderbook/on_chain/free_mint.py -o "$CONTRACT_OUT/free_mint"
PYTHONPATH=src .venv_opshin/bin/opshin build minting src/auth_nft_minting_tool/onchain/did_nft.py '{"bytes":"00000000000000000000000000000000000000000000000000000000"}' -o "$CONTRACT_OUT/did_nft"
echo "Compiled contracts under $CONTRACT_OUT"

echo "==> DID DEX frontend"
(cd src/did_dex_frontend && npm test && npm run build)

echo "==> Legacy minting frontend"
(cd src/auth_nft_minting_tool/frontend && CI=true npm test -- --watchAll=false && npm run build)

echo "==> Node package install checks"
(cd src/auth_nft_minting_tool && npm ci)
(cd src/auth_nft_minting_tool/server && npm ci)

echo "==> Offline verification complete"
