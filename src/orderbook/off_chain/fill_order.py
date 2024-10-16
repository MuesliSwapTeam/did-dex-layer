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

from src.orderbook.off_chain.util import sorted_utxos
from src.orderbook.on_chain.orderbook import opshin_orderbook_v3
from src.orderbook.off_chain.utils import get_signing_info, get_address, network
from src.orderbook.off_chain.utils.contracts import get_contract
from src.orderbook.off_chain.utils.from_script_context import from_address
from src.orderbook.off_chain.utils.network import context, show_tx
from src.orderbook.off_chain.utils.to_script_context import to_address, to_tx_out_ref


def main(
    name: str,
    max_amount: int = 50,
    steal: bool = False,
    take_more_reward: Optional[int] = None,
    steal_tokens: bool = False,
):
    payment_vkey, payment_skey, payment_address = get_signing_info(
        name, network=network
    )
    orderbook_v3_script, _, orderbook_v3_address = get_contract(
        "opshin_orderbook_v3", True, context
    )
    free_minting_contract_script, free_minting_contract_hash, _ = get_contract(
        "free_mint", True, context
    )
    (license_check_script, _, license_check_address) = get_contract(
        "license_check", True, context
    )

    # Find an order wanting to buy free_mint tokens
    found_orders = []
    for utxo in context.utxos(orderbook_v3_address):
        try:
            order_datum = opshin_orderbook_v3.Order.from_cbor(utxo.output.datum.cbor)
        except Exception as e:
            continue
        if order_datum.params.buy.policy_id != free_minting_contract_hash.payload:
            continue
        found_orders.append((utxo, order_datum))
    if not found_orders:
        print("No orders found")
        return

    # Find a valid license
    valid_license_utxo = None
    payment_utxos = context.utxos(payment_address)
    for utxo in payment_utxos:
        if utxo.output.amount.multi_asset.get(free_minting_contract_hash) is None:
            continue
        license_name = list(
            utxo.output.amount.multi_asset[free_minting_contract_hash].keys()
        )[0]
        license_expiry = int.from_bytes(license_name.payload, "big")
        if license_expiry < datetime.datetime.now().timestamp() * 1000:
            continue
        valid_license_utxo = utxo
        break
    if valid_license_utxo is None:
        print("No valid licenses found")
        return

    for amount_filled in range(min(len(found_orders), max_amount), 0, -1):
        found_orders_filtered = found_orders[:amount_filled]

        all_inputs_sorted = sorted_utxos(
            payment_utxos + [u[0] for u in found_orders_filtered]
        )
        license_input_index = all_inputs_sorted.index(valid_license_utxo)

        # Build the transaction
        builder = TransactionBuilder(context)
        builder.auxiliary_data = AuxiliaryData(
            data=AlonzoMetadata(
                metadata=Metadata({674: {"msg": ["MuesliSwap Fill Order"]}})
            )
        )
        for u in payment_utxos:
            builder.add_input(u)
        builder.mint = pycardano.MultiAsset()
        # add withdrawal which checks the license presence
        builder.add_withdrawal_script(
            license_check_script,
            pycardano.Redeemer(license_input_index),
        )
        builder.withdrawals = pycardano.Withdrawals(
            {
                bytes(
                    pycardano.Address(
                        staking_part=license_check_address.payment_part, network=network
                    )
                ): 0
            }
        )

        for i, (order_utxo, order_datum) in enumerate(found_orders_filtered):
            order_input_index = all_inputs_sorted.index(order_utxo)
            order_output_index = i
            fill_order_redeemer = pycardano.Redeemer(
                opshin_orderbook_v3.FullMatch(
                    input_index=order_input_index,
                    output_index=order_output_index,
                )
            )

            owner_address = from_address(order_datum.params.owner_address)
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