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
from pycardano.utils import fee
from pycardano import ExecutionUnits


class CustomTransactionBuilder(TransactionBuilder):
    """Custom TransactionBuilder that ensures reference script fees are properly calculated."""
    
    def _estimate_fee(self):
        """Override fee estimation to ensure reference script fees are properly calculated."""
        # Get reference script size
        ref_script_size = self._ref_script_size()
        
        # Recalculate execution units
        plutus_execution_units = ExecutionUnits(0, 0)
        for redeemer in self._redeemer_list:  # _redeemer_list is a property
            plutus_execution_units += redeemer.ex_units
        
        # Calculate fee with proper reference script fee
        # This ensures reference script fees are included correctly
        estimated_fee = fee(
            self.context,
            len(self._build_full_fake_tx().to_cbor()),
            plutus_execution_units.steps,
            plutus_execution_units.mem,
            ref_script_size,
        )
        
        # Add buffer if set
        if self.fee_buffer is not None:
            estimated_fee += self.fee_buffer
        
        # Add a small buffer (1.05x) for estimation variance in transaction size
        return int(estimated_fee * 1.05)


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
    ref_output.amount = Value(min_lvl)
    
    print(f"Required lovelace for reference UTxO: {ref_output.amount}")
    
    # Build the transaction (no metadata to minimize size)
    builder = CustomTransactionBuilder(context)
    # Select a single ADA-only UTxO to minimize tx size
    utxos = context.utxos(payment_address)
    # Rough fee buffer for selection (actual fee is computed later)
    required_coin = ref_output.amount.coin + 1_000_000
    ada_only_utxos = [u for u in utxos if len(u.output.amount.multi_asset) == 0]
    ada_only_utxos.sort(key=lambda u: u.output.amount.coin, reverse=True)

    selected_utxos = []
    total_coin = 0
    for u in ada_only_utxos:
        selected_utxos.append(u)
        total_coin += u.output.amount.coin
        if total_coin >= required_coin:
            break

    if total_coin < required_coin:
        # Fallback: use the largest available UTxO (may include multi-asset)
        utxos.sort(key=lambda u: u.output.amount.coin, reverse=True)
        if not utxos:
            raise RuntimeError("No UTxOs available to fund reference script deployment.")
        selected_utxos = [utxos[0]]

    for u in selected_utxos:
        builder.add_input(u)
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

