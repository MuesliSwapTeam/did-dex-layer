import datetime
from typing import Optional

import click
import pycardano
from pycardano import (
    TransactionBuilder,
    TransactionOutput,
    Asset,
    AuxiliaryData,
    AlonzoMetadata,
    Metadata,
    Network,
    ScriptHash,
)

from orderbook.off_chain.util import sorted_utxos
from orderbook.on_chain import orderbook
from orderbook.off_chain.utils.keys import get_signing_info, get_address
from orderbook.off_chain.utils.contracts import get_contract, find_reference_utxo
from orderbook.off_chain.utils.from_script_context import from_address
from orderbook.off_chain.utils.network import context, show_tx
from orderbook.off_chain.utils.to_script_context import to_address, to_tx_out_ref


DID_NFT_POLICY_ID = "672ae1e79585ad1543ef6b4b6c8989a17adcea3040f77ede128d9217"
DID_NFT_POLICY_ID = ScriptHash.from_primitive(DID_NFT_POLICY_ID)


class CustomTransactionBuilder(TransactionBuilder):
    """Custom TransactionBuilder that adds a buffer to the estimated fee."""
    
    def _estimate_fee(self):
        """Override fee estimation to ensure reference script fees are properly calculated."""
        from pycardano.utils import fee
        from pycardano import ExecutionUnits
        
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
@click.option("--use-reference-script/--no-reference-script", default=True,
              help="Use reference script if available (default: True)")
def main(
    name: str,
    use_reference_script: bool = True,
):
    payment_vkey, payment_skey, payment_address = get_signing_info(
        name, network=Network.TESTNET
    )
    orderbook_script, _, orderbook_v3_address = get_contract(
        "orderbook", False, context
    )

    # Try to find reference script UTxO
    ref_script_utxo = None
    if use_reference_script:
        ref_script_utxo = find_reference_utxo(
            "orderbook", context, [payment_address]
        )
        if ref_script_utxo:
            print(f"Using reference script: {ref_script_utxo.input.transaction_id}#{ref_script_utxo.input.index}")
        else:
            print("No reference script found, including script in transaction")

    # Find an order owned by this wallet
    owner_order_utxo = None
    owner_order_datum = None
    for utxo in context.utxos(orderbook_v3_address):
        try:
            order_datum = orderbook.Order.from_cbor(utxo.output.datum.cbor)
        except Exception as e:
            continue
        owner_pkh = order_datum.params.owner_pkh

        # Compare payment credential hash directly from pycardano Address
        if owner_pkh != payment_address.payment_part.payload:
            continue

        owner_order_datum = order_datum
        owner_order_utxo = utxo

    if owner_order_utxo is None:
        print("No orders found")
        return

    # Find a DID authentication NFT
    valid_did_utxo = None
    payment_utxos = context.utxos(payment_address)

    for utxo in payment_utxos:
        # Skip the reference script UTxO - we don't want to spend it
        if ref_script_utxo and utxo.input == ref_script_utxo.input:
            continue
        if utxo.output.amount.multi_asset.get(DID_NFT_POLICY_ID) is None:
            continue

        valid_did_utxo = utxo
        break
    
    if valid_did_utxo is None:
        print("No valid DID NFT found")
        return

    # Filter out reference script UTxO from payment inputs
    payment_utxos_filtered = [
        u for u in payment_utxos
        if not (ref_script_utxo and u.input == ref_script_utxo.input)
    ]

    # Use minimal inputs: DID NFT UTxO + one ADA-only UTxO for fees
    ada_only_utxos = [
        u for u in payment_utxos_filtered
        if len(u.output.amount.multi_asset) == 0 and u != valid_did_utxo
    ]
    ada_only_utxos.sort(key=lambda u: u.output.amount.coin)
    fee_utxo = ada_only_utxos[0] if ada_only_utxos else None

    selected_inputs = [valid_did_utxo]
    if fee_utxo:
        selected_inputs.append(fee_utxo)

    all_inputs_sorted = sorted_utxos(selected_inputs + [owner_order_utxo])
    did_input_index = all_inputs_sorted.index(valid_did_utxo)
    cancel_redeemer = pycardano.Redeemer(
        orderbook.CancelOrder(
            input_index=did_input_index,
        )
    )

    # Build the transaction
    builder = CustomTransactionBuilder(context)
    builder.auxiliary_data = AuxiliaryData(
        data=AlonzoMetadata(metadata=Metadata({674: {"msg": ["Cancel DID Order"]}}))
    )
    
    for u in selected_inputs:
        builder.add_input(u)

    # Add script input with reference script support
    if ref_script_utxo:
        # When using reference scripts, pass the reference UTxO as the script parameter
        # pycardano will automatically use it as a reference script
        builder.add_script_input(
            owner_order_utxo,
            script=ref_script_utxo,  # UTxO containing the reference script
            datum=None,
            redeemer=cancel_redeemer,
        )
    else:
        # Include full script in transaction
        builder.add_script_input(
            owner_order_utxo,
            orderbook_script,
            None,
            cancel_redeemer,
        )
    
    # Add collateral for script execution
    # Find a UTxO suitable for collateral (preferably pure ADA, but any will do)
    collateral_utxo = None
    for u in payment_utxos_filtered:
        if u.output.amount.coin >= 5_000_000:
            # Prefer pure ADA UTxOs
            if len(u.output.amount.multi_asset) == 0:
                collateral_utxo = u
                break
            elif collateral_utxo is None:
                collateral_utxo = u
    if collateral_utxo:
        builder.collaterals.append(collateral_utxo)
        print(f"Using collateral: {collateral_utxo.input.transaction_id}#{collateral_utxo.input.index}")
    else:
        print("WARNING: No suitable collateral UTxO found!")
    
    # Set minimum fee to avoid pycardano fee estimation bug
    # builder.fee = 600_000  # Removed in favor of CustomTransactionBuilder


    _return_value = owner_order_utxo.output.amount.coin

    print("return_value", _return_value)

    builder.add_output(
        TransactionOutput(
            address=payment_address,
            amount=_return_value,
        ),
    )

    # Sign the transaction
    signed_tx = builder.build_and_sign(
        signing_keys=[payment_skey],
        change_address=payment_address,
        auto_ttl_offset=1000,
        auto_validity_start_offset=0,
    )

    # Submit the transaction
    context.submit_tx(signed_tx.to_cbor())

    print(f"\nTransaction ID: {signed_tx.id}")
    show_tx(signed_tx)


if __name__ == "__main__":
    main()
