#!/usr/bin/env bash
# Convenience wrapper for optional live Preprod commands. In a clean checkout
# without private keys, it prints the missing context and exits successfully so
# README smoke checks do not fail on intentionally absent secrets.

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

PYTHON="${PYTHON:-$PROJECT_ROOT/.venv311/bin/python}"
CMD="${1:-check-context}"

required_files=(
  "src/keys/diddex_trader1.skey"
  "src/keys/diddex_trader1.test_addr"
  "src/keys/diddex_trader2.skey"
  "src/keys/diddex_trader2.test_addr"
  "src/keys/did_issuer.skey"
  "src/keys/did_issuer.test_addr"
)

missing_context() {
  local missing=0
  if [ ! -x "$PYTHON" ]; then
    echo "missing executable: $PYTHON"
    missing=1
  fi
  for file in "${required_files[@]}"; do
    if [ ! -f "$file" ]; then
      echo "missing file: $file"
      missing=1
    fi
  done
  return "$missing"
}

skip_if_missing_context() {
  if ! missing_context >/tmp/did-dex-live-missing.$$; then
    echo "SKIP: live Preprod command '$CMD' was not run."
    echo "Reason: this clean checkout is missing private/funded Preprod context:"
    cat /tmp/did-dex-live-missing.$$
    rm -f /tmp/did-dex-live-missing.$$
    echo "Add the supplied demo key bundle under src/keys/ and fund the wallets on Preprod to run live transactions."
    exit 0
  fi
  rm -f /tmp/did-dex-live-missing.$$
}

case "$CMD" in
  check-context)
    if missing_context; then
      echo "Live Preprod context is present."
    else
      echo "Live Preprod context is not configured. This is expected in a clean Docker checkout."
    fi
    ;;
  deploy-reference-script)
    skip_if_missing_context
    (cd src && "$PYTHON" -m orderbook.off_chain.deploy_reference_script diddex_trader1 orderbook)
    ;;
  mint-test-tokens)
    skip_if_missing_context
    (cd src && "$PYTHON" -m orderbook.off_chain.mint_free diddex_trader1 --token-name muesli --amount 1000000)
    (cd src && "$PYTHON" -m orderbook.off_chain.mint_free diddex_trader2 --token-name swap --amount 1000000)
    ;;
  check-did)
    skip_if_missing_context
    (cd src && "$PYTHON" - <<'PY'
from orderbook.off_chain.utils.keys import get_address
from orderbook.off_chain.utils.network import context
from did_dex_backend.config import DID_POLICY_ID

if context is None:
    print("SKIP: no Cardano chain context is available.")
    raise SystemExit(0)

for name in ("diddex_trader1", "diddex_trader2"):
    address = get_address(name)
    has_did = any(DID_POLICY_ID in str(utxo.output.amount.multi_asset) for utxo in context.utxos(address))
    print(f"{name} DID NFT: {'yes' if has_did else 'no'}")
PY
    )
    ;;
  place-order)
    skip_if_missing_context
    (cd src && "$PYTHON" -m orderbook.off_chain.place_order diddex_trader1 diddex_trader1 0 --sell-amount 10 --buy-amount 5)
    ;;
  cancel-order)
    skip_if_missing_context
    (cd src && "$PYTHON" -m orderbook.off_chain.cancel_order diddex_trader1 --no-reference-script)
    ;;
  *)
    echo "Usage: $0 [check-context|deploy-reference-script|mint-test-tokens|check-did|place-order|cancel-order]" >&2
    exit 2
    ;;
esac
