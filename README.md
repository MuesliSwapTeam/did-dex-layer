# Cardano DEX Protocol with DIDs Layer

This repository contains the documentation and code for the implementation of the project "Cardano DEX Protocol with DIDs Layer", proposed by the MuesliSwap team in Fund 10 of Project Catalyst.

## Table of Contents
- [Overview](#overview)
- [Installation](#installation)
- [System Architecture](#system-architecture)
- [Repository Structure](#repository-structure)
- [User Guide](#user-guide)
- [Advanced Features](#advanced-features)
- [Testing](#testing)
- [Demos](#demos)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)

## Overview

The Cardano DEX Protocol with DIDs Layer implements a decentralized exchange that integrates Decentralized Identifier (DID) authentication for enhanced security and compliance. The system ensures that while anyone can place trades, only users with verified DIDs can withdraw funds or cancel orders.

### Key Features
- **DID-Based Authentication**: Integration with Atala PRISM for user verification
- **Advanced Order Types**: Support for stop-loss orders, minimum fill amounts, and TWAP execution
- **Multi-DID Provider Support**: Compatibility with various DID verification levels
- **Compliance Framework**: DID requirements for counterparties in trading
- **Atomic Order Modification**: Real-time order updates without cancellation

## Installation

The project includes a pre-built PyCardano wheel in the `vendor/` directory, eliminating the need for external repository access.

### Quick Start (Recommended)

```bash
# Clone the repository
git clone <your-repo-url> did-dex-layer
cd did-dex-layer

# Run the installation script
./install.sh
```

The script will:
1. Check if you're in a virtual environment (creates one if needed)
2. Install the vendored PyCardano wheel
3. Install all other dependencies
4. Verify the installation

### Manual Installation

If you prefer to install manually:

```bash
# 1. Create and activate a virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 2. Install PyCardano from the vendored wheel
pip install vendor/pycardano-0.9.0-py3-none-any.whl

# 3. Install other dependencies
pip install -r requirements.txt

# 4. Verify installation
python -c "import pycardano; print(f'PyCardano {pycardano.__version__}')"
python -c "import opshin; print('OpShin OK')"
```

### Verification

After installation, verify everything works:

```bash
# Test imports
python -c "import pycardano, opshin, flask, pytest; print('All imports successful!')"

# Run tests
pytest src/tests/
```

## System Architecture

The system consists of three main components:

1. **DID Authentication Framework**: Handles user verification and NFT minting
2. **Enhanced Orderbook Contracts**: Smart contracts with integrated DID validation
3. **Frontend Interface**: User-friendly trading interface with DID integration

## Repository Structure

### Report

The directory `report` contains a detailed report of our research results, design sketch,
and implementation strategy as promised for Milestone 1 of the project.

### Atala PRISM Authenticanion Framework & On-chain Orderbook Smart Contracts  (Milestone 2)

The directory contains two parts. The first part is the connection to the DID plafrom that allows for the minting of DID NFTs. The second part is a modified orderbook DEX contract that asks a user to present a DID NFT when withdrawing funds from the swap smart contract (i.e. after an order is matched or the user cancels his order). This ensures that only users can swap/withdraw funds that have a valid DID authentication. The first part is based on the authentication tool developed ion [Atala Prism Voting Project](https://projectcatalyst.io/funds/10/f10-atala-prism-launch-ecosystem/dao-governance-x-atala-prism-by-muesliswap) and modified for use in this codebase. The second part is a new orderbook contract with added DID layer specifically developed for this project. 

### Protocol Explanation
This section provides a brief explanation of how the DID (Decentralized Identifier) layer functions. Anyone can place a trade by locking funds with the correct datum at the smart contract address. However, to withdraw or cancel an open position, a valid DID NFT (Non-Fungible Token) must be presented. For example, when a user initiates a transaction and later decides to cancel it, they must present the DID NFT during the cancellation process. The smart contract verifies that the policy ID of the DID NFT matches the policy ID of the DID minting tool. Since a "centralized entity" is responsible for verifying and issuing the DID, this validation can be conducted reliably. When a transaction is matched with another transaction, the funds remain in the contract until the user withdraws them. To do so, the user must use the cancel redeemer, which again requires presenting a valid DID NFT. The key benefit of this approach is that while anyone can participate in the protocol, only users who have verified their identity through the DID system will be able to withdraw funds. This ensures a layer of security and accountability within the protocol.

The system now supports multiple DID types (basic verified, accredited investors, business entities) and advanced order features including stop-loss orders, minimum fill amounts, TWAP execution, and atomic order modification. Orders can specify DID requirements for counterparties, enabling compliance-focused trading restrictions.


#### *DID Minting Tool*
The directory `src/auth_nft_minting_tool` contains the source code for
 - `frontend`: a DID authentication NFT minting tool that uses ProofSpace authentication
 - `hook`: a server that hosts an endpoint to be called by ProofSpace for receiving credentials and storing them in a DB
 - `server`: serving the backend used by `frontend` for connecting with the user DID DB populated by `hook`
 - `onchain`: the [OpShin](https://github.com/OpShin) contract used as a minting script for the DID authentication NFT

#### *Orderbook Smartcontracts with DID layer*
The directory `src/orderbook` contains the source code for on-chain/off-chain interactions of the orderbook with the relevant authentication NFT
 - `on-chain`: the on-chain smart contracts that are the core of the DEX including the DID layer, advanced order types (stop-loss, minimum fill, TWAP), and multi-DID provider support
 - `off-chain`: code to build examples to interact with the DEX smart contracts, including order modification and DID-based trading restrictions 


## User Guide

### Prerequisites

Before getting started, ensure you have completed the [Installation](#installation) steps above.

#### Additional Requirements for Testing
- **Python 3.9+**: Required for running the smart contracts and off-chain code
- **Node.js 16+**: Required for the frontend components (DID minting tool)
- **OpShin**: Smart contract compilation framework (installed via requirements.txt)

#### Network Requirements
- **Ogmios Endpoint**: Access to a Cardano node via Ogmios
- **Preprod Testnet Access**: For testing and demonstration

#### Configure Environment Variables

Set up your Cardano node connection:

```bash
export OGMIOS_API_HOST="localhost"
export OGMIOS_API_PROTOCOL="ws"
export OGMIOS_API_PORT="1337"
```

#### Optional: Frontend Setup

If using the DID minting tool frontend:

```bash
cd src/auth_nft_minting_tool/frontend
npm install
cd ../../..
```

### Initial Setup

The system can be initialized by deploying the smart contracts in the `onchain` directory using the scripts provided in the `offchain` directory.
For this, you need to have an Ogmios endpoint available and set the environment variables `OGMIOS_API_HOST`, `OGMIOS_API_PROTOCOL` and `OGMIOS_API_PORT` to the respective values (default `localhost`, `ws` and `1337`). 

Create and fund two wallets for the trading and voting part.
You can use the [testnet faucet](https://docs.cardano.org/cardano-testnet/tools/faucet/) to fund them, make sure to select `preprod` network!

```bash
cd src/orderbook
python3 create_keypair.py trader1
python3 create_keypair.py trader2
```

Fund these wallets using the [Cardano Preprod Testnet Faucet](https://docs.cardano.org/cardano-testnet/tools/faucet/). **Important**: Select the `preprod` network!

#### 2. Smart Contracts

The orderbook smart contracts are **pre-compiled** and included in the repository at `src/orderbook/on_chain/build/`.

If you need to recompile the contracts:

```bash
# Set Python path to include src directory
export PYTHONPATH="$(pwd)/src"

# Compile the orderbook contract
opshin build src/orderbook/on_chain/orderbook.py --recursion-limit 2000 -o src/orderbook/on_chain/build/orderbook

# Compile the free mint contract (for test tokens)
opshin build minting src/orderbook/on_chain/free_mint.py -o src/orderbook/on_chain/build/free_mint

# Compile the DID authentication NFT minting contract
opshin build minting src/auth_nft_minting_tool/onchain/atala_did_nft.py -o src/auth_nft_minting_tool/onchain/build/atala_did_nft
```

**Note:** The pre-compiled contracts in `build/` directories are ready to use. Recompilation is only needed if you modify the contract code.

#### 3. Mint Test Tokens

Create test tokens for trading. Please wait for the blockchain to confirm transaction 1 before calling the code for trader1. 

```bash
cd src/orderbook
python -m orderbook.off_chain.mint_free trader1
python -m orderbook.off_chain.mint_free trader2
```

### Basic Trading Operations

#### 1. Place an Order

Create a new trading order:

```bash
python -m orderbook.off_chain.place_order trader1 trader1 0
```

#### 2. Order Cancellation

Cancel an order (requires DID NFT from the test script):

```bash
python -m orderbook.off_chain.cancel_order trader1 [ORDER_ID]
```

This will create a new trade with `trader1` as owner`. You can now only cancel the order when presenting the DID NFT of trader 1. 

## Advanced Features

### Multi-DID Types and Requirements

The system supports multiple DID verification levels:

- **Basic Verified Users**: Standard DID authentication
- **Accredited Investors**: Enhanced verification for institutional trading
- **Business Entities**: Corporate account verification

#### Place Orders with DID Requirements

```bash
# Require accredited investor status for counterparty
python -m orderbook.off_chain.place_order trader1 trader2 0 --require-accredited-investor

# Require business entity verification
python -m orderbook.off_chain.place_order trader1 trader2 0 --require-business-entity
```

### Advanced Order Types

#### Stop-Loss Orders

Place orders with automatic execution triggers:

```bash
python -m orderbook.off_chain.place_order trader1 trader2 0 --stop-loss-price 50
```

#### Minimum Fill Orders

Ensure orders are only filled above a minimum threshold:

```bash
python -m orderbook.off_chain.place_order trader1 trader2 0 --minimum-fill-amount 100
```

### Order Management

#### Atomic Order Modification

Modify existing orders without cancellation:

```bash
# Update order amount
python -m orderbook.off_chain.modify_order trader1 --new-buy-amount 150

# Update order price
python -m orderbook.off_chain.modify_order trader1 --new-price 75

# Update stop-loss trigger
python -m orderbook.off_chain.modify_order trader1 --new-stop-loss 45
```

**Note:** Due to the large size of the orderbook smart contract (33KB), atomic order modification may exceed Cardano's 16KB transaction size limit. If you encounter "Transaction size exceeds the max limit" errors, use separate cancel and place order commands instead:

```bash
# Cancel the existing order
python -m orderbook.off_chain.cancel_order trader1

# Place a new order with updated parameters
python -m orderbook.off_chain.place_order trader1 trader1 0 --buy-amount 150
```

Future improvements will use reference scripts to overcome this limitation.

#### Bulk Order Operations

Execute multiple operations in a single transaction:

```bash
python -m orderbook.off_chain.bulk_payments trader1 --orders order1,order2,order3
```

## Testing

For comprehensive testing documentation, please refer to the [TEST_USER_GUIDE.md](TEST_USER_GUIDE.md).

### Quick Test Execution

Run the complete test suite:

```bash
python src/tests/run_all_tests.py
```

### Test Categories

- **Integration Tests**: End-to-end system testing
- **Contract Tests**: Smart contract validation
- **DID Authentication Tests**: Authentication flow testing
- **Performance Tests**: Load and stress testing

For detailed testing instructions, setup requirements, and troubleshooting, see the [Test User Guide](TEST_USER_GUIDE.md).

# Demos

## DID Authentication NFT Minting Tool

A hosted version of this authentication NFT minting tool can be found at [demo.did.muesliswap.com](https://demo.did.muesliswap.com).

## OrderbookSmart Contracts

We provide the following references to `preprod` testnet transactions showing relevant smart contracts interactions:


- [free mint script to mint test tokens](https://preprod.cexplorer.io/tx/6fe661e5206ab682c8289232c4bc2e2afb72fd640f127e9c669e6a013f0ff795)

- [creation of a new trade](https://preprod.cexplorer.io/tx/66073272374be9e8b2f006a6d858a5792838bce2fdb3d975e26207f874b7fd01)

- [cancel of a trade while presenting a DID Test NFT](https://preprod.cexplorer.io/tx/493b5d334a75d9655f749a027978d452f2a5b799f4622455cc0f0db359ac4148)

## Troubleshooting

### Common Issues and Solutions

#### Environment Setup Issues

**ModuleNotFoundError: No module named 'orderbook'**
- Ensure you're running commands from the project root directory
- Verify Python path includes the `src/` directory:
  ```bash
  export PYTHONPATH="${PYTHONPATH}:$(pwd)/src"
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
  curl -X POST http://localhost:1337 -H "Content-Type: application/json"
  ```

**Preprod testnet issues**
- Ensure wallets have sufficient ADA (minimum 5 ADA recommended)
- Verify you're using the correct network (preprod, not mainnet)
- Check testnet status at [Cardano status page](https://status.cardano.org/)

#### Smart Contract Issues

**Contract compilation failed**
- Verify OpShin installation:
  ```bash
  pip install opshin
  ```
- Ensure PYTHONPATH is set correctly:
  ```bash
  export PYTHONPATH="$(pwd)/src"
  ```
- The recursion limit of 2000 is sufficient for the orderbook contract
- Clear build cache and recompile if issues persist:
  ```bash
  rm -rf src/orderbook/on_chain/build/orderbook/
  opshin compile spending src/orderbook/on_chain/orderbook.py --recursion-limit 2000 -o src/orderbook/on_chain/build/orderbook
  ```

#### DID Authentication Issues

**DID NFT minting failed**
- Verify the DID demo website is accessible
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
  python src/tests/run_all_tests.py --performance-only
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

# Internal Testing Report

## Overview

Internal testing for the Cardano DEX Protocol with DIDs Layer focused on validating the DID minting tool and the orderbook smart contracts. The key objectives were to test the minting of DID NFTs and to ensure the DID layer is integrated properly within the DEX orderbook for user authentication during trades.

## Test Plan

### DID Minting Tool
Testing was done by accessing the [DID demo website](https://demo.did.muesliswap.com), where a DID NFT was minted, and the transaction was verified on the Preprod Testnet. The minting tool, backend, and on-chain contract interactions worked as expected.

### Orderbook Smart Contracts
The orderbook smart contracts were deployed using the provided scripts and verified on the Preprod Testnet. Both on-chain and off-chain interactions, including withdrawing matched funds and canceling trades, required valid DID NFTs, ensuring the authentication layer functioned correctly.

## Test Cases and Results

1. **DID Minting Tool**  
   Minting a DID NFT was successful. Transaction verified on Preprod.

2. **Orderbook Contract Deployment**  
   Smart contracts were successfully deployed and accessible via the testnet explorer.

3. **Token Minting and Trading**  
   Test tokens were minted, and a trade was placed with `trader1`. Cancellation without the DID NFT failed as expected, while presenting the DID NFT allowed successful cancellation.

4. **On-chain/Off-chain Interaction**  
   Off-chain code generated valid transactions, interacting correctly with the on-chain orderbook contracts. DID checks were enforced during all interactions.
