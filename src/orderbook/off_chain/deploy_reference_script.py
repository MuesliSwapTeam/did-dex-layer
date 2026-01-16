"""
Deploy reference scripts on-chain.

Reference scripts allow the contract to be stored on-chain once, then referenced
in subsequent transactions instead of including the full script each time.
This reduces transaction sizes and fees.

Usage:
    python -m orderbook.off_chain.deploy_reference_script <wallet_name> [contract_name]
    
Example:
    python -m orderbook.off_chain.deploy_reference_script trader1 orderbook
"""

import click
from pycardano import (
    TransactionBuilder,
    TransactionOutput,
    min_lovelace,
    Value,
)

from orderbook.off_chain.utils.keys import get_signing_info, network
from orderbook.off_chain.utils.contracts import get_contract, get_ref_utxo, save_reference_utxo
from orderbook.off_chain.utils.network import context, show_tx


@click.command()
@click.argument("name")
@click.argument("contract_name", default="orderbook")
def main(name: str, contract_name: str):
    """Deploy a reference script for the specified contract.
    
    Args:
        name: Wallet name to use for deployment
        contract_name: Name of the contract to deploy (default: orderbook)
    """
    payment_vkey, payment_skey, payment_address = get_signing_info(
        name, network=network
    )
    
    # Get the contract script
    contract_script, contract_hash, contract_address = get_contract(
        contract_name, False, context
    )
    
    # Check if reference script already exists at our address
    existing_ref = get_ref_utxo(contract_script, context, payment_address)
    if existing_ref is not None:
        print(f"Reference script for '{contract_name}' already deployed!")
        print(f"UTxO: {existing_ref.input.transaction_id}#{existing_ref.input.index}")
        return
    
    print(f"Deploying reference script for '{contract_name}'...")
    print(f"Contract hash: {contract_hash}")
    print(f"Script size: {len(bytes(contract_script))} bytes")
    
    # Build a transaction output that holds the reference script
    ref_output = TransactionOutput(
        address=payment_address,
        amount=0,  # Will be set to min_lovelace
        script=contract_script,
    )
    
    # Calculate minimum lovelace required for the output
    min_lvl = min_lovelace(context, ref_output)
    ref_output.amount = Value(min_lvl + 1000000)  # Add 1 ADA buffer
    
    print(f"Required lovelace for reference UTxO: {ref_output.amount}")
    
    # Build the transaction (no metadata to minimize size)
    builder = TransactionBuilder(context)
    builder.add_input_address(payment_address)
    builder.add_output(ref_output)
    
    # Sign and submit
    signed_tx = builder.build_and_sign(
        signing_keys=[payment_skey],
        change_address=payment_address,
    )
    
    context.submit_tx(signed_tx.to_cbor())
    
    print(f"\nReference script deployed successfully!")
    print(f"Transaction ID: {signed_tx.id}")
    
    # Find the output index for the reference script and save it
    for i, output in enumerate(signed_tx.transaction_body.outputs):
        if output.script == contract_script:
            print(f"Reference UTxO: {signed_tx.id}#{i}")
            # Save the reference script location
            save_reference_utxo(
                contract_name,
                str(signed_tx.id),
                i,
                str(payment_address)
            )
            print(f"Saved reference script location to build/reference_scripts.json")
            break
    
    show_tx(signed_tx)


if __name__ == "__main__":
    main()

