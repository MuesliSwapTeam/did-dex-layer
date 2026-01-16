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

        if owner_pkh != to_address(payment_address).payment_credential.credential_hash:
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

    all_inputs_sorted = sorted_utxos(payment_utxos_filtered + [owner_order_utxo])
    did_input_index = all_inputs_sorted.index(valid_did_utxo)
    cancel_redeemer = pycardano.Redeemer(
        orderbook.CancelOrder(
            input_index=did_input_index,
        )
    )

    # Build the transaction
    builder = TransactionBuilder(context)
    builder.auxiliary_data = AuxiliaryData(
        data=AlonzoMetadata(metadata=Metadata({674: {"msg": ["Cancel DID Order"]}}))
    )
    
    for u in payment_utxos_filtered:
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
    builder.fee = 600_000  # 0.6 ADA should cover script execution

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
