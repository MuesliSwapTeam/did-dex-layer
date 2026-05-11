# Cardano DEX Protocol with DIDs Layer

This repository contains the documentation and code for the implementation of the project "Cardano DEX Protocol with DIDs Layer", proposed by the MuesliSwap team in Fund 10 of Project Catalyst.

## Table of Contents
- [Overview](#overview)
- [Installation](#installation)
- [System Architecture](#system-architecture)
- [Repository Structure](#repository-structure)
- [User Guide](#user-guide)
- [Testing](#testing)
- [Demos](#demos)
- [Troubleshooting](#troubleshooting)

## Overview

The Cardano DEX Protocol with DIDs Layer implements a decentralized exchange that integrates Decentralized Identifier (DID) authentication for enhanced security and compliance. The system ensures that while anyone can place trades, only users with verified DIDs can withdraw funds or cancel orders.

### Key Features
- **DID-Based Authentication**: Permissioned DID NFT minting for verified users
- **Orderbook Trading**: Preprod order placement, cancellation, and fill transaction builders
- **Frontend Interface**: Vite + React interface for DID registration and trading

## Installation

```bash
# Clone the repository
git clone https://github.com/MuesliSwapTeam/did-dex-layer.git did-dex-layer
cd did-dex-layer
```

### Clean Setup

The installer is non-interactive and creates both Python environments plus all Node dependencies. It is the recommended path for a clean Docker container or a reviewer machine.

```bash
./install.sh
./scripts/verify_offline.sh
```

`./scripts/verify_offline.sh` runs every check that does not require private keys, funded wallets, Ogmios, Blockfrost availability, or a running Cardano node.

### Manual Runtime Environment

Use this environment for tests, backend, frontend-backed transaction builders, and live Preprod orderbook commands if you are not using `./install.sh`.

```bash
python3.11 -m venv .venv311
.venv311/bin/python -m pip install --upgrade pip
.venv311/bin/python -m pip install \
  "cbor2<6" "pycardano>=0.19,<0.20" "fastapi>=0.101,<0.102" "uvicorn[standard]" \
  fastapi-cache2 slowapi peewee==3.17.0 pyjwt==2.8.0 cryptography==36.0.2 \
  pytest pytest-asyncio pytest-cov flask flask-cors ogmios fire blockfrost-python \
  "aiohttp[speedups]" async-lru gelidum orjson psutil click
.venv311/bin/python -m pip install --no-deps "opshin==0.19.1"
.venv311/bin/python -c "import pycardano, fastapi, uvicorn, pytest, ogmios, opshin; print('runtime OK')"
```

### Contract Compiler Environment

Use this environment only when recompiling OpShin contracts. The repository includes the required PyCardano 0.9 wheel in `vendor/`.

```bash
python3.11 -m venv .venv_opshin
.venv_opshin/bin/python -m pip install --upgrade pip
.venv_opshin/bin/python -m pip install vendor/pycardano-0.9.0-py3-none-any.whl
.venv_opshin/bin/python -m pip install "opshin==0.19.1" fire
.venv_opshin/bin/python -c "import pycardano, opshin, fire; print('compiler OK')"
```

### Frontend Dependencies

```bash
cd src/did_dex_frontend
npm ci
cd ../..
```

After installation, verify the active frontend and Python tests:

```bash
.venv311/bin/python -m pytest src/tests/
cd src/did_dex_frontend && npm test && npm run build && cd ../..
```

## System Architecture

The system consists of three main components:

1. **DID Authentication Framework**: Handles user verification and NFT minting
2. **Enhanced Orderbook Contracts**: Smart contracts with integrated DID validation
3. **Frontend Interface**: User-friendly trading interface with DID integration

## DID DEX Application

The new DID DEX application replaces the retired ProofSpace minting dependency with a lightweight permissioned registration flow:

- `src/did_dex_backend`: FastAPI backend for DID registration, DID status checks, order indexing, analytics, and unsigned transaction construction.
- `src/did_dex_frontend`: Vite + React + TypeScript frontend for DID registration and orderbook trading.
- `src/auth_nft_minting_tool/onchain/did_nft.py`: permissioned DID NFT minting policy. It requires both the issuer signature and recipient wallet signature and mints exactly one DID NFT.

### Run The DID DEX Locally

Backend terminal:

```bash
.venv311/bin/python -m uvicorn --app-dir src did_dex_backend.main:app --reload --host 0.0.0.0 --port 8000
```

Frontend terminal:

```bash
cd src/did_dex_frontend
npm run dev
```

For production/testnet serving, build the frontend and start the backend. The FastAPI app serves `src/did_dex_frontend/dist` when it exists.

```bash
cd src/did_dex_frontend
npm run build
cd ../..
.venv311/bin/python -m uvicorn --app-dir src did_dex_backend.main:app --host 0.0.0.0 --port 8000
```

The backend uses checked-in Preprod pair/script configuration and runtime SQLite state under `runtime/did_dex/`. The issuer signing key must be available as `src/keys/did_issuer.skey`; the DID minting script should be compiled/deployed with that issuer key hash as its script parameter before a live Preprod smoke test.

## Repository Structure

### Report

The directory `report` contains a detailed report of our research results, design sketch,
and implementation strategy as promised for Milestone 1 of the project.


### Protocol Explanation
This section provides a brief explanation of how the DID (Decentralized Identifier) layer functions. Anyone can place a trade by locking funds with the correct datum at the smart contract address. However, to withdraw or cancel an open position, a valid DID NFT (Non-Fungible Token) must be presented. For example, when a user initiates a transaction and later decides to cancel it, they must present the DID NFT during the cancellation process. The smart contract verifies that the policy ID of the DID NFT matches the policy ID of the DID minting tool. Since a "centralized entity" is responsible for verifying and issuing the DID, this validation can be conducted reliably. When a transaction is matched with another transaction, the funds remain in the contract until the user withdraws them. To do so, the user must use the cancel redeemer, which again requires presenting a valid DID NFT. The key benefit of this approach is that while anyone can participate in the protocol, only users who have verified their identity through the DID system will be able to withdraw funds. This ensures a layer of security and accountability within the protocol.

#### *DID Minting Tool*
The active DID minting flow is implemented by `src/did_dex_backend` together with the permissioned on-chain policy in `src/auth_nft_minting_tool/onchain/did_nft.py`.

#### *Orderbook Smartcontracts with DID layer*
The directory `src/orderbook` contains the source code for on-chain/off-chain interactions of the orderbook with the relevant authentication NFT
 - `on-chain`: the on-chain smart contracts that are the core of the DEX including the DID layer
 - `off-chain`: code to build and submit testnet transactions against the DEX smart contracts


## User Guide

### Prerequisites

Before getting started, ensure you have completed the [Installation](#installation) steps above.

#### Additional Requirements for Testing
- **Python 3.9-3.11**: Required for running the smart contracts and off-chain code (Python 3.12+ is not compatible with opshin versions that work with pycardano 0.9.0)
- **Node.js 18+**: Required for frontend installation, tests, and builds.
- **OpShin**: Smart contract compilation framework (installed in `.venv_opshin`)

#### Network Requirements
- **No node required for offline verification**: `./scripts/verify_offline.sh` does not need Ogmios, Blockfrost availability, private keys, or funded wallets.
- **Live Preprod commands only**: Transaction submission requires the supplied demo key bundle under `src/keys/`, funded Preprod wallets, and reachable chain context.

#### Configure Environment Variables

Optional Ogmios settings:

```bash
export OGMIOS_API_HOST="localhost"
export OGMIOS_API_PROTOCOL="ws"
export OGMIOS_API_PORT="1337"
```

### Initial Setup

#### 1. Wallets

Wallet files are intentionally ignored by git. For the live Preprod commands below, place the supplied demo key bundle in `src/keys/` before running transactions.

```bash
./scripts/live_preprod.sh check-context
```

Optional fresh wallet generation:

```bash
cd src/orderbook
WALLET_PREFIX="reviewer_$(date +%s)"
../../.venv311/bin/python create_keypair.py "${WALLET_PREFIX}_trader1"
../../.venv311/bin/python create_keypair.py "${WALLET_PREFIX}_trader2"
cd ../..  # Return to repository root
```

Fresh wallets must be funded on Preprod and registered through the DID DEX app before they can replace the demo wallet names in live transaction commands.

#### 2. Smart Contracts

The orderbook smart contracts are **pre-compiled** and included in the repository at `src/orderbook/on_chain/build/`.

Verify contract compilation without modifying checked-in build artifacts:

```bash
# Use the contract compiler venv. OpShin 0.19 requires PyCardano 0.9,
# while live Conway-era transactions use the runtime .venv311 PyCardano 0.19.
export PYTHONPATH="$(pwd)/src"
CONTRACT_OUT="$(mktemp -d "${TMPDIR:-/tmp}/did-dex-contracts.XXXXXX")"

# Compile the orderbook contract
.venv_opshin/bin/opshin build spending src/orderbook/on_chain/orderbook.py --recursion-limit 3000 -o "$CONTRACT_OUT/orderbook"

# Compile the free mint contract (for test tokens)
.venv_opshin/bin/opshin build minting src/orderbook/on_chain/free_mint.py -o "$CONTRACT_OUT/free_mint"

# Compile the DID authentication NFT minting contract with a deterministic dummy issuer.
.venv_opshin/bin/opshin build minting src/auth_nft_minting_tool/onchain/did_nft.py '{"bytes":"00000000000000000000000000000000000000000000000000000000"}' -o "$CONTRACT_OUT/did_nft"

echo "Compiled contracts under $CONTRACT_OUT"
```

**Note:** The pre-compiled contracts in `build/` directories are ready to use. Recompilation is only needed if you modify the contract code. Use Python 3.9-3.11 with opshin 0.19.1 for compilation. For live DID NFT deployment, compile `src/auth_nft_minting_tool/onchain/did_nft.py` with the real issuer payment key hash from `src/keys/did_issuer.skey`.

#### 3. Deploy Reference Script (Recommended)

Deploying the orderbook contract as a reference script keeps the protocol script discoverable on-chain. The current backend includes the compact V1 script directly in cancel/fill transactions for Conway-era PyCardano compatibility.

```bash
./scripts/live_preprod.sh deploy-reference-script
```

This stores the contract on-chain and saves the reference script location automatically.

**Deployed Reference Script (Preprod Testnet)**:
- **Reference Script UTxO**: `f54f22ea202fbad0dad17d191b63af091d5afd98929fc0f750c49b6848b4f637#0`
- **Contract Hash**: `0146cf769189d1b86e56e14d5c76c490163e238526839c4126563f13`
- **Explorer Link**: [View on Cexplorer](https://preprod.cexplorer.io/tx/f54f22ea202fbad0dad17d191b63af091d5afd98929fc0f750c49b6848b4f637)

**Note:** Reference scripts are optional but recommended. If not deployed, the full script will be included in each transaction.

#### 4. Mint Test Tokens

Create test tokens for trading. Wait for each transaction to confirm before spending its change output in the next command.

```bash
./scripts/live_preprod.sh mint-test-tokens
```

#### 5. DID NFT Requirement

A DID NFT is required to cancel orders or withdraw matched funds. The supplied demo wallets already hold DID NFTs for the current policy. For new wallets, use the DID DEX frontend registration flow backed by `src/did_dex_backend`.

```bash
./scripts/live_preprod.sh check-did
```

### Basic Trading Operations

#### 1. Place an Order

Create a new trading order:

```bash
./scripts/live_preprod.sh place-order
```

#### 2. Order Cancellation

Cancel an order (requires DID NFT):

```bash
./scripts/live_preprod.sh cancel-order
```

The smart contract verifies that the DID NFT policy ID matches the expected DID minting policy before allowing the cancellation. 


## Testing

For comprehensive testing documentation, please refer to the [TEST_USER_GUIDE.md](TEST_USER_GUIDE.md).

### Quick Test Execution

Run the complete test suite:

```bash
./scripts/verify_offline.sh
```

### Test Categories

- **Integration Tests**: End-to-end system testing
- **Contract Tests**: Smart contract validation
- **DID Authentication Tests**: Authentication flow testing
- **Performance Tests**: Load and stress testing

For detailed testing instructions, setup requirements, and troubleshooting, see the [Test User Guide](TEST_USER_GUIDE.md).

# Demos

## Orderbook Smart Contracts

We provide the following references to `preprod` testnet transactions showing relevant smart contracts interactions:


- [free mint script to mint test tokens](https://preprod.cexplorer.io/tx/6fe661e5206ab682c8289232c4bc2e2afb72fd640f127e9c669e6a013f0ff795)

- [creation of a new trade](https://preprod.cexplorer.io/tx/66073272374be9e8b2f006a6d858a5792838bce2fdb3d975e26207f874b7fd01)

- [cancel of a trade while presenting a DID Test NFT](https://preprod.cexplorer.io/tx/493b5d334a75d9655f749a027978d452f2a5b799f4622455cc0f0db359ac4148)

Additional smoke-test transactions submitted from this checkout:

- [mint test tokens for diddex_trader1](https://preprod.cexplorer.io/tx/36bddde7e20723ca95e5b49a6328f567e707ee5da78755c6b5fb89e0ca4c5804)
- [mint test tokens for diddex_trader2](https://preprod.cexplorer.io/tx/6f0deabf9ed88c90a6372579caf6838ae6a0ade373046aab4f0dffdce76f7401)
- [place order](https://preprod.cexplorer.io/tx/bdec4382ebcfaec156ec2793fee53946969651909a017b885777a39d596f6130)
- [cancel order with DID NFT](https://preprod.cexplorer.io/tx/d0c3a4e91ec98a4c144b91d18ed18f7fc523f120ec5178f8e4598d6145c961f3)

## Troubleshooting

### Common Issues and Solutions

#### Environment Setup Issues

**ModuleNotFoundError: No module named 'orderbook'**
- Ensure you're running commands from the project root directory
- Verify Python path includes the `src/` directory:
  ```bash
  export PYTHONPATH="${PYTHONPATH:-}:$(pwd)/src"
  ```

**Command not found: python**
- On macOS/Linux, use `python3` instead of `python`
- Ensure Python 3.9+ is installed:
  ```bash
  python3 --version
  ```

#### Network and Connection Issues

**Ogmios connection failed**
- Verify Ogmios is running on the specified host/port
- Check environment variables:
  ```bash
  echo $OGMIOS_API_HOST $OGMIOS_API_PROTOCOL $OGMIOS_API_PORT
  ```
- Test connection manually:
  ```bash
  curl -fsS -X POST http://localhost:1337 -H "Content-Type: application/json" || true
  ```

**Preprod testnet issues**
- Ensure wallets have sufficient ADA (minimum 5 ADA recommended)
- Verify you're using the correct network (preprod, not mainnet)
- Check testnet status at [Cardano status page](https://status.cardano.org/)

#### Smart Contract Issues

**Contract compilation failed**
- Verify OpShin installation:
  ```bash
  .venv_opshin/bin/python -c "import opshin; print('OpShin OK')"
  ```
- Ensure PYTHONPATH is set correctly:
  ```bash
  export PYTHONPATH="$(pwd)/src"
  ```
- The recursion limit of 3000 is recommended for the orderbook contract
- Clear build cache and recompile if issues persist:
  ```bash
  export PYTHONPATH="$(pwd)/src"
  CONTRACT_OUT="$(mktemp -d "${TMPDIR:-/tmp}/did-dex-contracts.XXXXXX")"
  .venv_opshin/bin/opshin build spending src/orderbook/on_chain/orderbook.py --recursion-limit 3000 -o "$CONTRACT_OUT/orderbook"
  ```

#### DID Authentication Issues

**DID NFT minting failed**
- Verify the DID DEX backend and frontend are running
- Check wallet connectivity in browser
- Ensure sufficient ADA for minting fees (minimum 2 ADA)
- Try refreshing the page and reconnecting wallet

**Order cancellation rejected**
- Verify DID NFT is in the correct wallet
- Check NFT policy ID matches the expected DID policy
- Ensure NFT hasn't been accidentally spent or burned

### Performance Optimization

#### Slow Transaction Building
- Use bulk operations when possible
- Optimize UTXO selection by consolidating small UTXOs
- Consider parallel processing for multiple operations

#### Memory Usage
- Monitor system resources during large operations:
  ```bash
  .venv311/bin/python src/tests/run_all_tests.py --performance-only
  ```

### Getting Help

If you encounter issues not covered here:

1. Check the [Test User Guide](TEST_USER_GUIDE.md) for testing-specific troubleshooting
2. Review recent transactions on [Preprod Explorer](https://preprod.cexplorer.io/)
3. Join the MuesliSwap community discussions
4. Create an issue on the GitHub repository with:
   - Error messages
   - System information (OS, Python version)
   - Steps to reproduce
