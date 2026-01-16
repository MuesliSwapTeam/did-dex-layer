"""
Simple script to mint example DID NFTs for testing the orderbook.

This script mints a DID NFT using the atala_did_nft minting contract.
The NFT can be used with the orderbook for authentication.
"""
import click
import hashlib
from pycardano import (
    TransactionBuilder,
    Redeemer,
    AuxiliaryData,
    AlonzoMetadata,
    Metadata,
    TransactionOutput,
    MultiAsset,
    Value,
    AssetName,
    Asset,
    Network,
)

from orderbook.off_chain.utils.keys import get_signing_info, get_address
from orderbook.off_chain.utils.network import show_tx, context


def get_did_contract():
    """Load the DID NFT minting contract."""
    from pathlib import Path
    from pycardano import PlutusV2Script, plutus_script_hash
    
    # Path to the built DID contract
    build_dir = Path(__file__).parent.parent.parent / "auth_nft_minting_tool/onchain/build/atala_did_nft"
    script_cbor_path = build_dir / "script.cbor"
    
    if not script_cbor_path.exists():
        raise FileNotFoundError(
            f"DID contract not found at {script_cbor_path}. "
            "Please compile the contract first using: "
            "opshin build minting src/auth_nft_minting_tool/onchain/atala_did_nft.py -o src/auth_nft_minting_tool/onchain/build/atala_did_nft"
        )
    
    with open(script_cbor_path) as f:
        contract_cbor_hex = f.read().strip()
    
    contract_cbor = bytes.fromhex(contract_cbor_hex)
    contract_plutus_script = PlutusV2Script(contract_cbor)
    contract_script_hash = plutus_script_hash(contract_plutus_script)
    
    return contract_plutus_script, contract_script_hash


@click.command()
@click.argument("name")
@click.option(
    "--did-identifier",
    type=str,
    default=None,
    help="DID identifier string (defaults to wallet address hash if not provided)",
)
@click.option(
    "--asset-name",
    type=str,
    default=None,
    help="Asset name for the NFT (defaults to hash of DID identifier)",
)
def main(
    name: str,
    did_identifier: str = None,
    asset_name: str = None,
):
    """
    Mint a DID NFT for the specified wallet.
    
    This creates a simple DID NFT that can be used with the orderbook for authentication.
    The NFT is minted using the atala_did_nft contract.
    
    Example:
        python -m did_example_mint.mint_did_nft trader1
    """
    # Get wallet info
    payment_vkey, payment_skey, payment_address = get_signing_info(
        name, network=Network.TESTNET
    )
    
    # Generate DID identifier if not provided (use address hash)
    if did_identifier is None:
        # Use the bech32 encoded address string as the DID identifier
        did_identifier = payment_address.to_primitive()
    
    # Generate asset name if not provided (use hash of DID identifier)
    if asset_name is None:
        did_hash = hashlib.sha256(did_identifier.encode()).digest()[:32]
        asset_name_bytes = did_hash
    else:
        # Convert string to bytes if needed
        if isinstance(asset_name, str):
            # If it's a hex string, decode it; otherwise encode as UTF-8
            try:
                asset_name_bytes = bytes.fromhex(asset_name)
            except ValueError:
                asset_name_bytes = asset_name.encode()
        else:
            asset_name_bytes = asset_name
    
    # Load the DID minting contract
    # The policy ID is automatically computed from the contract hash
    try:
        did_contract_script, did_contract_hash = get_did_contract()
    except FileNotFoundError as e:
        click.echo(f"❌ Error: {e}", err=True)
        return
    
    # Policy ID is computed from the contract script hash
    policy_id = did_contract_hash.to_primitive().hex()
    click.echo(f"Using Policy ID: {policy_id} (computed from contract)")
    
    # Build the transaction
    builder = TransactionBuilder(context)
    builder.auxiliary_data = AuxiliaryData(
        data=AlonzoMetadata(
            metadata=Metadata({674: {"msg": ["Mint Example DID NFT"]}})
        )
    )
    builder.add_input_address(payment_address)
    
    # Add minting script with redeemer
    # The redeemer format depends on the contract - using a simple redeemer
    builder.add_minting_script(did_contract_script, Redeemer(0))
    
    # Create the NFT asset
    nft_asset = MultiAsset(
        {did_contract_hash: Asset({AssetName(asset_name_bytes): 1})}
    )
    
    # Add output with the NFT
    builder.add_output(
        TransactionOutput(
            address=payment_address,
            amount=Value(coin=2000000, multi_asset=nft_asset),
        )
    )
    builder.mint = nft_asset
    
    # Sign and submit
    try:
        signed_tx = builder.build_and_sign(
            signing_keys=[payment_skey],
            change_address=payment_address,
            auto_ttl_offset=1000,
            auto_validity_start_offset=0,
        )
        
        # Submit the transaction
        context.submit_tx(signed_tx.to_cbor())
        
        click.echo("✅ DID NFT minted successfully!")
        show_tx(signed_tx)
        click.echo(f"\nNFT Details:")
        click.echo(f"  Policy ID: {did_contract_hash.to_primitive().hex()}")
        click.echo(f"  Asset Name: {asset_name_bytes.hex()}")
        click.echo(f"  DID Identifier: {did_identifier}")
        
    except Exception as e:
        click.echo(f"❌ Error minting NFT: {e}", err=True)
        raise


if __name__ == "__main__":
    main()

