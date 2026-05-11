"""
Modify Order Script

This script allows users to modify existing orders by canceling the old order 
and placing a new one in the same transaction. This provides atomic order
modification without the risk of having no active order between operations.
"""

import datetime
from typing import Optional
from pathlib import Path
import click
import pycardano
from pycardano import (
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
from orderbook.off_chain.utils.keys import get_signing_info, get_address, network
from orderbook.off_chain.utils.contracts import get_contract, find_reference_utxo
from orderbook.off_chain.utils.from_script_context import from_address
from orderbook.off_chain.utils.network import context, show_tx
from orderbook.off_chain.utils.to_script_context import to_address, to_tx_out_ref
from orderbook.off_chain.utils.transaction_builder import TransactionBuilder

# DID policy IDs for validation
DID_POLICY_FILE = (
    Path(__file__).resolve().parents[2]
    / "auth_nft_minting_tool"
    / "onchain"
    / "build"
    / "did_nft"
    / "script.policy_id"
)
DID_NFT_POLICY_ID = bytes.fromhex(DID_POLICY_FILE.read_text().strip())
DID_NFT_POLICY_ID = ScriptHash.from_primitive(DID_NFT_POLICY_ID)


@click.command()
@click.argument("name")
@click.option(
    "--new-sell-amount",
    type=int,
    help="New amount of token to sell (if different from original)",
)
@click.option(
    "--new-buy-amount",
    type=int,
    help="New amount of token to buy (if different from original)",
)
@click.option(
    "--new-stop-loss-price",
    type=float,
    help="New stop-loss trigger price (optional)",
)
@click.option(
    "--new-min-fill-amount",
    type=int,
    help="New minimum fill amount for this order",
)
@click.option(
    "--new-twap-interval",
    type=int,
    help="New TWAP interval in minutes",
)
@click.option(
    "--new-max-slippage",
    type=float,
    help="New maximum slippage in percentage",
)
@click.option(
    "--require-accredited-investor",
    is_flag=True,
    help="Require counterparty to be an accredited investor",
)
@click.option(
    "--require-business-entity",
    is_flag=True,
    help="Require counterparty to be a business entity",
)
@click.option(
    "--allow-non-did-trading",
    is_flag=True,
    help="Allow trading with users without DIDs",
)
@click.option(
    "--use-reference-script/--no-reference-script",
    default=True,
    help="Use reference script if available (default: True)",
)
def main(
    name: str,
    new_sell_amount: Optional[int] = None,
    new_buy_amount: Optional[int] = None,
    new_stop_loss_price: Optional[float] = None,
    new_min_fill_amount: Optional[int] = None,
    new_twap_interval: Optional[int] = None,
    new_max_slippage: Optional[float] = None,
    require_accredited_investor: bool = False,
    require_business_entity: bool = False,
    allow_non_did_trading: bool = False,
    use_reference_script: bool = True,
):
    """
    Modify an existing order by canceling it and placing a new one in the same transaction.

    This ensures atomic order modification - either both operations succeed or both fail,
    preventing the user from being left without an active order.

    Examples:

    # Modify order to new buy amount
    python -m orderbook.off_chain.modify_order trader1 --new-buy-amount 50

    # Change order to require accredited investors only
    python -m orderbook.off_chain.modify_order trader2 --require-accredited-investor
    """

    payment_vkey, payment_skey, payment_address = get_signing_info(
        name, network=Network.TESTNET
    )
    orderbook_script, _, orderbook_address = get_contract("orderbook", False, context)
    free_minting_contract_script, free_minting_contract_hash, _ = get_contract(
        "free_mint", False
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

    # Find user's existing order
    user_order_utxo = None
    user_order_datum = None
    for utxo in context.utxos(orderbook_address):
        try:
            order_datum = orderbook.Order.from_cbor(utxo.output.datum.cbor)
        except Exception as e:
            continue

        owner_pkh = order_datum.params.owner_pkh
        # Compare payment credential hash directly from pycardano Address
        user_payment_pkh = payment_address.payment_part.payload

        if owner_pkh != user_payment_pkh:
            continue

        user_order_datum = order_datum
        user_order_utxo = utxo
        break

    if user_order_utxo is None:
        print("No existing order found for user")
        return

    print(f"Found existing order with buy amount: {user_order_datum.buy_amount}")

    # Find user's DID authentication NFT
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
        print("No valid DID NFT found - required for order modification")
        return

    # Filter out reference script UTxO from payment inputs
    payment_utxos_filtered = [
        u for u in payment_utxos
        if not (ref_script_utxo and u.input == ref_script_utxo.input)
    ]

    # Prepare new order parameters based on existing order and modifications
    original_params = user_order_datum.params

    # Use new values if provided, otherwise keep original values
    sell_amount = (
        new_sell_amount
        if new_sell_amount is not None
        else get_sell_amount_from_utxo(user_order_utxo, original_params.sell)
    )
    buy_amount = (
        new_buy_amount if new_buy_amount is not None else user_order_datum.buy_amount
    )

    # Filter payment UTXOs to only include necessary ones (reduce transaction size)
    # We need: DID NFT utxo + minimal ADA utxos for fees
    # With reference scripts, the transaction is much smaller
    necessary_utxos = [valid_did_utxo]

    # Add up to 2 ADA-only UTXOs for fees (the minimum needed)
    ada_only_count = 0
    for utxo in payment_utxos_filtered:
        if utxo == valid_did_utxo:
            continue
        # Only include UTXOs with pure ADA (no multi-assets)
        if len(utxo.output.amount.multi_asset) == 0:
            necessary_utxos.append(utxo)
            ada_only_count += 1
            if ada_only_count >= 2:
                break

    # Build transaction that cancels old order and places new one
    all_inputs_sorted = sorted_utxos(necessary_utxos + [user_order_utxo])
    order_input_index = all_inputs_sorted.index(user_order_utxo)

    cancel_redeemer = pycardano.Redeemer(
        orderbook.CancelOrder(
            input_index=order_input_index,
        )
    )

    # Use standard TransactionBuilder with increased fee buffer to account for:
    # - Reference script fees (30KB+ scripts)
    # - Plutus script execution (cancel + place)
    # - Large datums with advanced features
    # - Transaction size estimation variance
    builder = TransactionBuilder(context)
    builder.fee_buffer = 1_500_000  # Add 1.5 ADA buffer for cancel + place operations
    builder.auxiliary_data = AuxiliaryData(
        data=AlonzoMetadata(
            metadata=Metadata({674: {"msg": ["MuesliSwap Modify Order"]}})
        )
    )

    # Add necessary user inputs
    for u in necessary_utxos:
        builder.add_input(u)

    # Cancel the existing order - use reference script if available
    if ref_script_utxo:
        # When using reference scripts, pass the reference UTxO as the script parameter
        # pycardano will automatically use it as a reference script
        builder.add_script_input(
            user_order_utxo,
            script=ref_script_utxo,  # UTxO containing the reference script
            datum=None,
            redeemer=cancel_redeemer,
        )
    else:
        # Include full script in transaction
        builder.add_script_input(
            user_order_utxo,
            orderbook_script,
            None,
            cancel_redeemer,
        )

    # Create new order with modified parameters
    beneficiary_address = from_address(original_params.owner_address)
    beneficiary_pkh = beneficiary_address.payment_part

    # Token configuration (keep same tokens as original order)
    sell_token = (
        pycardano.ScriptHash(original_params.sell.policy_id),
        pycardano.AssetName(original_params.sell.token_name),
    )
    buy_token = (
        pycardano.ScriptHash(original_params.buy.policy_id),
        pycardano.AssetName(original_params.buy.token_name),
    )

    # Create new order parameters
    min_utxo = original_params.min_utxo
    return_reward = original_params.return_reward

    expiry_ms = int(
        (datetime.datetime.now() + datetime.timedelta(days=1)).timestamp() * 1000
    )

    new_params = orderbook.OrderParams(
        beneficiary_pkh.payload,
        to_address(beneficiary_address),
        orderbook.Token(buy_token[0].payload, buy_token[1].payload),
        orderbook.Token(sell_token[0].payload, sell_token[1].payload),
        1,  # Allow partial fills
        orderbook.FinitePOSIXTime(expiry_ms),
        return_reward,
        min_utxo,
    )

    # Make new order datum
    new_datum = orderbook.Order(
        new_params,
        buy_amount,
        orderbook.Nothing(),
        return_reward,
    )

    # Add new order output
    builder.add_output(
        TransactionOutput(
            address=orderbook_address,
            amount=pycardano.Value(
                coin=min_utxo + return_reward,
                multi_asset=pycardano.MultiAsset(
                    {sell_token[0]: Asset({sell_token[1]: sell_amount})}
                ),
            ),
            datum=new_datum,
        )
    )

    # Sign and submit the transaction
    signed_tx = builder.build_and_sign(
        signing_keys=[payment_skey],
        change_address=payment_address,
    )

    context.submit_tx(signed_tx.to_cbor())
    show_tx(signed_tx)

    print(f"✓ Successfully modified order:")
    print(f"  Old buy amount: {user_order_datum.buy_amount}")
    print(f"  New buy amount: {buy_amount}")
    if new_sell_amount:
        print(f"  New sell amount: {sell_amount}")
    if new_stop_loss_price:
        print(f"  New stop-loss price: {new_stop_loss_price}")
    if require_accredited_investor:
        print(f"  Now requires accredited investor counterparty")
    if require_business_entity:
        print(f"  Now requires business entity counterparty")


def get_sell_amount_from_utxo(utxo, sell_token):
    """Extract the sell token amount from the UTXO"""
    sell_policy_id = pycardano.ScriptHash(sell_token.policy_id)
    sell_token_name = pycardano.AssetName(sell_token.token_name)

    if utxo.output.amount.multi_asset.get(sell_policy_id):
        return utxo.output.amount.multi_asset[sell_policy_id].get(sell_token_name, 0)
    return 0


if __name__ == "__main__":
    main()
