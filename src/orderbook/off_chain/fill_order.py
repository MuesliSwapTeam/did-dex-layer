import datetime
from typing import Optional

import click
import fire
import pycardano
from pycardano import (
    TransactionBuilder,
    TransactionOutput,
    Asset,
    AuxiliaryData,
    AlonzoMetadata,
    Metadata,
)

from orderbook.off_chain.util import sorted_utxos
from orderbook.on_chain import orderbook
from orderbook.off_chain.utils.keys import get_signing_info, get_address, network
from orderbook.off_chain.utils.contracts import get_contract, find_reference_utxo
from orderbook.off_chain.utils.from_script_context import from_address
from orderbook.off_chain.utils.network import context, show_tx
from orderbook.off_chain.utils.to_script_context import to_address, to_tx_out_ref
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


def should_trigger_stop_loss(order_datum, market_price: float) -> bool:
    """Check if a stop-loss order should be triggered based on current market price."""
    if (
        not hasattr(order_datum.params, "advanced_features")
        or order_datum.params.advanced_features is None
    ):
        return False

    try:
        advanced_features = order_datum.params.advanced_features
        if advanced_features.stop_loss_price_num > 0 and market_price is not None:
            stop_loss_price = (
                advanced_features.stop_loss_price_num
                / advanced_features.stop_loss_price_den
            )
            return market_price <= stop_loss_price
    except:
        pass
    return False


def meets_minimum_fill(order_datum, fill_amount: int) -> bool:
    """Check if the fill amount meets the minimum fill requirement."""
    if (
        not hasattr(order_datum.params, "advanced_features")
        or order_datum.params.advanced_features is None
    ):
        return True

    try:
        advanced_features = order_datum.params.advanced_features
        return fill_amount >= advanced_features.min_fill_amount
    except:
        return True


def get_appropriate_redeemer(
    order_datum,
    fill_amount: int,
    market_price: Optional[float],
    order_input_index: int,
    order_output_index: int,
):
    """Determine the appropriate redeemer type based on order characteristics."""
    # Check if this should be a stop-loss match
    if should_trigger_stop_loss(order_datum, market_price):
        price_num = int(market_price * 10000) if market_price else 10000
        price_den = 10000
        return orderbook.StopLossMatch(
            input_index=order_input_index,
            output_index=order_output_index,
            filled_amount=fill_amount,
            trigger_price_num=price_num,
            trigger_price_den=price_den,
        )

    # Check if this is a full match or partial match
    if fill_amount >= order_datum.buy_amount:
        return orderbook.FullMatch(
            input_index=order_input_index,
            output_index=order_output_index,
        )
    else:
        return orderbook.PartialMatch(
            input_index=order_input_index,
            output_index=order_output_index,
            filled_amount=fill_amount,
        )


def main(
    name: str,
    max_amount: int = 50,
    steal: bool = False,
    take_more_reward: Optional[int] = None,
    steal_tokens: bool = False,
    enable_advanced_matching: bool = True,
    current_market_price: Optional[float] = None,
    use_reference_script: bool = True,
):
    payment_vkey, payment_skey, payment_address = get_signing_info(
        name, network=network
    )
    orderbook_v3_script, _, orderbook_v3_address = get_contract(
        "orderbook", False, context
    )
    free_minting_contract_script, free_minting_contract_hash, _ = get_contract(
        "free_mint", False, context
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

    # Find an order wanting to buy free_mint tokens
    found_orders = []
    for utxo in context.utxos(orderbook_v3_address):
        try:
            order_datum = orderbook.Order.from_cbor(utxo.output.datum.cbor)
        except Exception as e:
            continue
        if order_datum.params.buy.policy_id != free_minting_contract_hash.payload:
            continue
        found_orders.append((utxo, order_datum))
    if not found_orders:
        print("No orders found")
        return

    payment_utxos = context.utxos(payment_address)
    
    # Filter out reference script UTxO from payment inputs
    payment_utxos_filtered = [
        u for u in payment_utxos 
        if not (ref_script_utxo and u.input == ref_script_utxo.input)
    ]

    for amount_filled in range(min(len(found_orders), max_amount), 0, -1):
        found_orders_filtered = found_orders[:amount_filled]

        all_inputs_sorted = sorted_utxos(
            payment_utxos_filtered + [u[0] for u in found_orders_filtered]
        )

        # Build the transaction
        builder = CustomTransactionBuilder(context)
        builder.auxiliary_data = AuxiliaryData(
            data=AlonzoMetadata(
                metadata=Metadata({674: {"msg": ["MuesliSwap Fill Order"]}})
            )
        )
        for u in payment_utxos_filtered:
            builder.add_input(u)
        builder.mint = pycardano.MultiAsset()

        for i, (order_utxo, order_datum) in enumerate(found_orders_filtered):
            order_input_index = all_inputs_sorted.index(order_utxo)
            order_output_index = i

            # Calculate fill amount (for now, assume full fill)
            fill_amount = order_datum.buy_amount

            # Check if the fill meets minimum requirements
            if enable_advanced_matching and not meets_minimum_fill(
                order_datum, fill_amount
            ):
                print(f"Order {i} does not meet minimum fill requirement, skipping")
                continue

            # Get the appropriate redeemer based on order type
            if enable_advanced_matching:
                redeemer_data = get_appropriate_redeemer(
                    order_datum,
                    fill_amount,
                    current_market_price,
                    order_input_index,
                    order_output_index,
                )
            else:
                # Default to FullMatch for backward compatibility
                redeemer_data = orderbook.FullMatch(
                    input_index=order_input_index,
                    output_index=order_output_index,
                )

            fill_order_redeemer = pycardano.Redeemer(redeemer_data)

            owner_address = from_address(order_datum.params.owner_address)
            
            # Add script input - with or without reference script
            if ref_script_utxo:
                # Pass reference UTxO as script parameter - pycardano uses it as reference script
                builder.add_script_input(
                    order_utxo,
                    script=ref_script_utxo,  # UTxO containing the reference script
                    datum=None,
                    redeemer=fill_order_redeemer,
                )
            else:
                builder.add_script_input(
                    order_utxo,
                    orderbook_v3_script,
                    None,
                    fill_order_redeemer,
                )
                
            _taken_reward = take_more_reward or order_datum.batch_reward
            sell_token = order_datum.params.sell
            sell_token = (
                pycardano.ScriptHash(sell_token.policy_id),
                pycardano.AssetName(sell_token.token_name),
            )
            sell_amount = order_utxo.output.amount.multi_asset.get(sell_token[0]).get(
                sell_token[1]
            )
            sell_asset = pycardano.Value(
                multi_asset=pycardano.MultiAsset(
                    {sell_token[0]: pycardano.Asset({sell_token[1]: sell_amount})}
                )
            )
            buy_token = order_datum.params.buy
            buy_token = (
                pycardano.ScriptHash(buy_token.policy_id),
                pycardano.AssetName(buy_token.token_name),
            )
            buy_amount = order_datum.buy_amount
            buy_asset = pycardano.Value(
                multi_asset=pycardano.MultiAsset(
                    {buy_token[0]: pycardano.Asset({buy_token[1]: buy_amount})}
                )
            )

            if not steal_tokens:
                _return_value = (
                    order_utxo.output.amount - _taken_reward - sell_asset + buy_asset
                )
            else:
                _return_value = order_utxo.output.amount - _taken_reward - sell_asset
            builder.add_output(
                TransactionOutput(
                    address=owner_address if not steal else payment_address,
                    amount=_return_value,
                    datum=to_tx_out_ref(order_utxo.input),
                ),
            )
            builder.mint += buy_asset.multi_asset
        if builder.mint:
            builder.add_minting_script(
                free_minting_contract_script, pycardano.Redeemer(0)
            )
        else:
            builder.mint = None

        # Sign the transaction
        try:
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
            print(f"filled {amount_filled} orders")
            break
        except Exception as e:
            if amount_filled == 1:
                raise e
            print(f"{amount_filled} failed, trying less ({e})")
            continue


if __name__ == "__main__":
    fire.Fire(main)
