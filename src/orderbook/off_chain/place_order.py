import datetime

import click
import pycardano
from pycardano import (
    TransactionOutput,
    Asset,
    AuxiliaryData,
    AlonzoMetadata,
    Metadata,
)

from orderbook.on_chain import orderbook
from orderbook.off_chain.utils.keys import get_signing_info, get_address, network
from orderbook.off_chain.utils.contracts import get_contract
from orderbook.off_chain.utils.from_script_context import from_address
from orderbook.off_chain.utils.network import context, show_tx
from orderbook.off_chain.utils.to_script_context import to_address
from orderbook.off_chain.utils.transaction_builder import TransactionBuilder

free_minting_contract_script, free_minting_contract_hash, _ = get_contract(
    "free_mint", False, context
)


@click.command()
@click.argument("name")
@click.argument("beneficiary")
# Seller (0) or Buyer (1)
@click.argument("role", type=int)
@click.option(
    "--number",
    type=int,
    default=1,
    help="Number of orders placed",
)
@click.option(
    "--sell-amount",
    type=int,
    default=300,
    help="Amount of token to sell",
)
@click.option(
    "--buy-amount",
    type=int,
    default=100,
    help="Amount of token to buy",
)
@click.option(
    "--stop-loss-price",
    type=float,
    help="Stop-loss trigger price (optional)",
)
@click.option(
    "--min-fill-amount",
    type=int,
    default=0,
    help="Minimum fill amount for this order (0 means no minimum)",
)
@click.option(
    "--twap-interval",
    type=int,
    default=0,
    help="TWAP interval in minutes (0 means disabled)",
)
@click.option(
    "--max-slippage",
    type=float,
    default=0.0,
    help="Maximum slippage in percentage (0 means no limit)",
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
    beneficiary: str,
    role: int,
    number: int,
    sell_amount: int,
    buy_amount: int,
    stop_loss_price: float = None,
    min_fill_amount: int = 0,
    twap_interval: int = 0,
    max_slippage: float = 0.0,
    require_accredited_investor: bool = False,
    require_business_entity: bool = False,
    allow_non_did_trading: bool = False,
):
    payment_vkey, payment_skey, payment_address = get_signing_info(
        name, network=network
    )
    orderbook_v3_script, _, orderbook_v3_address = get_contract(
        "orderbook", False, context
    )

    # Build the transaction
    # Use standard TransactionBuilder with increased fee buffer to account for:
    # - Reference script fees
    # - Datum size variations (especially with advanced features)
    # - Transaction size estimation variance
    # Higher buffer needed as pycardano's estimator may underestimate with large datums
    builder = TransactionBuilder(context)
    builder.fee_buffer = 800_000  # Add 0.8 ADA buffer for datum + multi-output operations
    builder.add_input_address(payment_address)
    builder.auxiliary_data = AuxiliaryData(
        data=AlonzoMetadata(
            metadata=Metadata({674: {"msg": ["MuesliSwap Place Order"]}})
        )
    )

    for _ in range(number):
        # Get the beneficiary VerificationKeyHash (PubKeyHash)
        if beneficiary == "random":
            beneficiary_pkh = pycardano.PaymentVerificationKey.from_signing_key(
                pycardano.PaymentSigningKey.generate()
            ).hash()
            beneficiary_address = pycardano.Address(
                payment_part=beneficiary_pkh,
                network=network,
            )
        else:
            beneficiary_address = get_address(beneficiary)
            beneficiary_pkh = beneficiary_address.payment_part

        sell_token = (free_minting_contract_hash, pycardano.AssetName(b"muesli"))
        buy_token = (free_minting_contract_hash, pycardano.AssetName(b"swap"))
        if role:
            sell_token, buy_token = buy_token, sell_token

        # Create the vesting datum
        min_utxo = 2300000
        return_reward = 650000

        expiry_ms = int(
            (datetime.datetime.now() + datetime.timedelta(days=1)).timestamp() * 1000
        )

        params = orderbook.OrderParams(
            beneficiary_pkh.payload,
            to_address(beneficiary_address),
            orderbook.Token(buy_token[0].payload, buy_token[1].payload),
            orderbook.Token(sell_token[0].payload, sell_token[1].payload),
            1,
            orderbook.FinitePOSIXTime(expiry_ms),
            return_reward,
            min_utxo,
        )
        # Make datum
        datum = orderbook.Order(
            params,
            buy_amount,
            orderbook.Nothing(),
            return_reward,
        )

        builder.add_output(
            TransactionOutput(
                address=orderbook_v3_address,
                amount=pycardano.Value(
                    coin=min_utxo + return_reward,
                    multi_asset=pycardano.MultiAsset(
                        {sell_token[0]: Asset({sell_token[1]: sell_amount})}
                    ),
                ),
                datum=datum,
            )
        )
    
    # Sign the transaction
    signed_tx = builder.build_and_sign(
        signing_keys=[payment_skey],
        change_address=payment_address,
    )

    # Submit the transaction
    context.submit_tx(signed_tx.to_cbor())

    show_tx(signed_tx)


if __name__ == "__main__":
    main()
