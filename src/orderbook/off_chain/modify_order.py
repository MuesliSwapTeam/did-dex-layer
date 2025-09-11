"""
Modify Order Script

This script allows users to modify existing orders by canceling the old order 
and placing a new one in the same transaction. This provides atomic order
modification without the risk of having no active order between operations.
"""

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
    ScriptHash
)

from orderbook.off_chain.util import sorted_utxos
from orderbook.on_chain import orderbook
from orderbook.off_chain.utils.keys import get_signing_info, get_address, network
from orderbook.off_chain.utils.contracts import get_contract
from orderbook.off_chain.utils.from_script_context import from_address
from orderbook.off_chain.utils.network import context, show_tx
from orderbook.off_chain.utils.to_script_context import to_address, to_tx_out_ref

# DID policy IDs for validation
DID_NFT_POLICY_ID = bytes.fromhex("672ae1e79585ad1543ef6b4b6c8989a17adcea3040f77ede128d9217")
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
):
    """
    Modify an existing order by canceling it and placing a new one in the same transaction.
    
    This ensures atomic order modification - either both operations succeed or both fail,
    preventing the user from being left without an active order.
    
    Examples:
    
    # Modify order to new buy amount
    python modify_order.py alice --new-buy-amount 150
    
    # Change order to require accredited investors only
    python modify_order.py bob --require-accredited-investor
    
    # Update stop-loss price and minimum fill amount
    python modify_order.py charlie --new-stop-loss-price 1.5 --new-min-fill-amount 50
    """
    
    payment_vkey, payment_skey, payment_address = get_signing_info(
        name, network=Network.TESTNET
    )
    orderbook_script, _, orderbook_address = get_contract(
        "orderbook", False, context
    )
    free_minting_contract_script, free_minting_contract_hash, _ = get_contract(
        "free_mint", False
    )

    # Find user's existing order
    user_order_utxo = None
    user_order_datum = None
    for utxo in context.utxos(orderbook_address):
        try:
            order_datum = orderbook.Order.from_cbor(utxo.output.datum.cbor)
        except Exception as e:
            continue
        
        owner_pkh = order_datum.params.owner_pkh
        user_payment_pkh = to_address(payment_address).payment_credential.credential_hash
        
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
        if utxo.output.amount.multi_asset.get(DID_NFT_POLICY_ID) is None:
            continue
        valid_did_utxo = utxo
        break
    
    if valid_did_utxo is None:
        print("No valid DID NFT found - required for order modification")
        return

    # Prepare new order parameters based on existing order and modifications
    original_params = user_order_datum.params
    
    # Use new values if provided, otherwise keep original values
    sell_amount = new_sell_amount if new_sell_amount is not None else get_sell_amount_from_utxo(user_order_utxo, original_params.sell)
    buy_amount = new_buy_amount if new_buy_amount is not None else user_order_datum.buy_amount
    
    # Create advanced features (merge new and existing)
    stop_loss_price = new_stop_loss_price
    min_fill_amount = new_min_fill_amount if new_min_fill_amount is not None else 0
    twap_interval = new_twap_interval if new_twap_interval is not None else 0
    max_slippage = new_max_slippage if new_max_slippage is not None else 0.0
    
    # If original order had advanced features, preserve them unless overridden
    if not isinstance(original_params.advanced_features, orderbook.Nothing):
        orig_features = original_params.advanced_features
        if stop_loss_price is None and orig_features.stop_loss_price_num > 0:
            stop_loss_price = orig_features.stop_loss_price_num / orig_features.stop_loss_price_den
        if new_min_fill_amount is None:
            min_fill_amount = orig_features.min_fill_amount
        if new_twap_interval is None:
            twap_interval = orig_features.twap_interval // (60 * 1000)  # Convert back to minutes
        if new_max_slippage is None:
            max_slippage = orig_features.max_slippage_bps / 100.0
    
    # Build transaction that cancels old order and places new one
    all_inputs_sorted = sorted_utxos(payment_utxos + [user_order_utxo])
    did_input_index = all_inputs_sorted.index(valid_did_utxo)
    
    cancel_redeemer = pycardano.Redeemer(
        orderbook.CancelOrder(
            input_index=did_input_index,
        )
    )

    builder = TransactionBuilder(context)
    builder.auxiliary_data = AuxiliaryData(
        data=AlonzoMetadata(
            metadata=Metadata({674: {"msg": ["MuesliSwap Modify Order"]}})
        )
    )
    
    # Add all user inputs
    for u in payment_utxos:
        builder.add_input(u)
    
    # Cancel the existing order
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
        pycardano.AssetName(original_params.sell.token_name)
    )
    buy_token = (
        pycardano.ScriptHash(original_params.buy.policy_id),
        pycardano.AssetName(original_params.buy.token_name)
    )

    # Create advanced features if any are specified
    advanced_features = orderbook.Nothing()
    if stop_loss_price or min_fill_amount > 0 or twap_interval > 0 or max_slippage > 0:
        stop_loss_num = int(stop_loss_price * 10000) if stop_loss_price else 0
        stop_loss_den = 10000 if stop_loss_price else 1
        twap_interval_ms = twap_interval * 60 * 1000
        slippage_bps = int(max_slippage * 100)
        
        advanced_features = orderbook.AdvancedOrderFeatures(
            stop_loss_num,
            stop_loss_den,
            min_fill_amount,
            twap_interval_ms,
            slippage_bps
        )

    # Create DID requirements if any are specified
    did_requirements = orderbook.Nothing()
    if require_accredited_investor or require_business_entity or allow_non_did_trading:
        accepted_did_types = []
        
        if require_accredited_investor:
            accredited_did_type = orderbook.DIDType(
                orderbook.ACCREDITED_INVESTOR_POLICY_ID,
                b"",  # Any token name
                2     # Accredited investor level
            )
            accepted_did_types.append(accredited_did_type)
        
        if require_business_entity:
            business_did_type = orderbook.DIDType(
                orderbook.BUSINESS_ENTITY_POLICY_ID,
                b"",  # Any token name
                3     # Business entity level
            )
            accepted_did_types.append(business_did_type)
        
        did_requirements = orderbook.DIDRequirements(
            accepted_did_types,
            1,  # Require counterparty DID
            1 if allow_non_did_trading else 0  # Allow non-DID trading
        )
    elif not isinstance(original_params.did_requirements, orderbook.Nothing):
        # Preserve original DID requirements if no new ones specified
        did_requirements = original_params.did_requirements

    # Create new order parameters
    min_utxo = original_params.min_utxo
    return_reward = original_params.return_reward
    
    new_params = orderbook.OrderParams(
        beneficiary_pkh.payload,
        to_address(beneficiary_address),
        orderbook.Token(buy_token[0].payload, buy_token[1].payload),
        orderbook.Token(sell_token[0].payload, sell_token[1].payload),
        1,  # Allow partial fills
        orderbook.FinitePOSIXTime(
            int(datetime.datetime.now().timestamp() * 1000)
        ),
        return_reward,
        min_utxo,
        advanced_features,
        did_requirements,
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
