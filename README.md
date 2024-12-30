# Cardano DEX Protocol with DIDs Layer

This repository contains the documentation and code for the implementation
of the project "Cardano DEX Protocol with DIDs Layer", proposed by the MuesliSwap team
in Fund 10 of Project Catalyst. 

## Structure

### Report

The directory `report` contains a detailed report of our research results, design sketch,
and implementation strategy as promised for Milestone 1 of the project.

### Atala PRISM Authenticanion Framework & On-chain Orderbook Smart Contracts  (Milestone 2)

The directory contains two parts. The first part is the connection to the DID plafrom that allows for the minting of DID NFTs. The second part is a modified orderbook DEX contract that asks a user to present a DID NFT when withdrawing funds from the swap smart contract (i.e. after an order is matched or the user cancels his order). This ensures that only users can swap/withdraw funds that have a valid DID authentication. The first part is based on the authentication tool developed ion [Atala Prism Voting Project](https://projectcatalyst.io/funds/10/f10-atala-prism-launch-ecosystem/dao-governance-x-atala-prism-by-muesliswap) and modified for use in this codebase. The second part is a new orderbook contract with added DID layer specifically developed for this project. 

### Protocol Explanation
This section provides a brief explanation of how the DID (Decentralized Identifier) layer functions. Anyone can place a trade by locking funds with the correct datum at the smart contract address. However, to withdraw or cancel an open position, a valid DID NFT (Non-Fungible Token) must be presented. For example, when a user initiates a transaction and later decides to cancel it, they must present the DID NFT during the cancellation process. The smart contract verifies that the policy ID of the DID NFT matches the policy ID of the DID minting tool. Since a "centralized entity" is responsible for verifying and issuing the DID, this validation can be conducted reliably. When a transaction is matched with another transaction, the funds remain in the contract until the user withdraws them. To do so, the user must use the cancel redeemer, which again requires presenting a valid DID NFT. The key benefit of this approach is that while anyone can participate in the protocol, only users who have verified their identity through the DID system will be able to withdraw funds. This ensures a layer of security and accountability within the protocol.


#### *DID Minting Tool*
The directory `src/auth_nft_minting_tool` contains the source code for
 - `frontend`: a DID authentication NFT minting tool that uses ProofSpace authentication
 - `hook`: a server that hosts an endpoint to be called by ProofSpace for receiving credentials and storing them in a DB
 - `server`: serving the backend used by `frontend` for connecting with the user DID DB populated by `hook`
 - `onchain`: the [OpShin](https://github.com/OpShin) contract used as a minting script for the DID authentication NFT

#### *Orderbook Smartcontracts with DID layer*
The directory `src/orderbook` contains the source code for on-chain/off-chain interactions of the orderbook with the relevant authentication NFT
 - `on-chain`: the on-chain smart contracts that are the core of the DEX including the DID layer
 - `off-chain`: code to build examples to interact with the DEX smart contracts 


### Instructions for using 

The system can be initialized by deploying the smart contracts in the `onchain` directory using the scripts provided in the `offchain` directory.
For this, you need to have an Ogmios endpoint available and set the environment variables `OGMIOS_API_HOST`, `OGMIOS_API_PROTOCOL` and `OGMIOS_API_PORT` to the respective values (default `localhost`, `ws` and `1337`). 

Create and fund two wallets for the trading and voting part.
You can use the [testnet faucet](https://docs.cardano.org/cardano-testnet/tools/faucet/) to fund them, make sure to select `preprod` network!

```bash
cd src/orderbook
python3 create_key_pair.py trader1
python3 -m orderbook.create_key_pair trader2
```

Then, build the smart contracts. Note that this requires the [`plutonomy-cli`](https://github.com/OpShin/plutonomy-cli) executable present in the `PATH` environment variable.

```bash
cd src/orderbook/on_chain
opshin compile spending orderbook.py --recursion-limit 2000
``` 

We need to mint additional tokens for trading. For this we can use the mint_free script. You can for example call

```bash
python -m orderbook.off_chain.mint_free trader1

```

You can for example create a first trade for `trader1` by calling

```bash
python -m orderbook.off_chain.place_order trader1 trader1 0

```

This will create a new trade with `trader1` as owner`. You can now only cancel the order when presenting the DID NFT of trader 1. To do this you can mint an authentication NFT through our [DID demo website](https://demo.did.muesliswap.com) and then send it to the wallets of the respective traders. To then cancel the order you can call the relvant cancelation code which constructs the correct transaction and presents the DID NFT during cancelation. 

```bash
python3 -m contracts.offchain.staking.init --wallet voter
```

# Demos

## DID Authentication NFT Minting Tool

A hosted version of this authentication NFT minting tool can be found at [demo.did.muesliswap.com](https://demo.did.muesliswap.com).

## OrderbookSmart Contracts

We provide the following references to `preprod` testnet transactions showing relevant smart contracts interactions:


- [free mint script to mint test tokens](https://preprod.cexplorer.io/tx/6fe661e5206ab682c8289232c4bc2e2afb72fd640f127e9c669e6a013f0ff795)

- [creation of a new trade](https://preprod.cexplorer.io/tx/66073272374be9e8b2f006a6d858a5792838bce2fdb3d975e26207f874b7fd01)

- [cancel of a trade while presenting a DID Test NFT](https://preprod.cexplorer.io/tx/493b5d334a75d9655f749a027978d452f2a5b799f4622455cc0f0db359ac4148)

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
