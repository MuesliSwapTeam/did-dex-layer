import datetime

import click
import pycardano
from pycardano import (
    TransactionBuilder,
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
    builder = TransactionBuilder(context)
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

        # Create advanced features if any are specified
        advanced_features = orderbook.Nothing()
        if (
            stop_loss_price
            or min_fill_amount > 0
            or twap_interval > 0
            or max_slippage > 0
        ):
            # Convert stop-loss price to ratio (using 10000 as denominator for precision)
            stop_loss_num = int(stop_loss_price * 10000) if stop_loss_price else 0
            stop_loss_den = 10000 if stop_loss_price else 1

            # Convert TWAP interval from minutes to milliseconds
            twap_interval_ms = twap_interval * 60 * 1000

            # Convert slippage percentage to basis points
            slippage_bps = int(max_slippage * 100)

            advanced_features = orderbook.AdvancedOrderFeatures(
                stop_loss_num,
                stop_loss_den,
                min_fill_amount,
                twap_interval_ms,
                slippage_bps,
            )

        # Create DID requirements if any are specified
        did_requirements = orderbook.Nothing()
        if (
            require_accredited_investor
            or require_business_entity
            or allow_non_did_trading
        ):
            accepted_did_types = []

            if require_accredited_investor:
                accredited_did_type = orderbook.DIDType(
                    orderbook.ACCREDITED_INVESTOR_POLICY_ID,
                    b"",  # Any token name
                    2,  # Accredited investor level
                )
                accepted_did_types.append(accredited_did_type)

            if require_business_entity:
                business_did_type = orderbook.DIDType(
                    orderbook.BUSINESS_ENTITY_POLICY_ID,
                    b"",  # Any token name
                    3,  # Business entity level
                )
                accepted_did_types.append(business_did_type)

            # If no specific types required but allow_non_did_trading is false, require basic DID
            if (
                not require_accredited_investor
                and not require_business_entity
                and not allow_non_did_trading
            ):
                basic_did_type = orderbook.DIDType(
                    orderbook.DID_NFT_POLICY_ID,
                    b"",  # Any token name
                    1,  # Basic verified level
                )
                accepted_did_types.append(basic_did_type)

            did_requirements = orderbook.DIDRequirements(
                accepted_did_types,
                1,  # Require counterparty DID
                1 if allow_non_did_trading else 0,  # Allow non-DID trading
            )

        params = orderbook.OrderParams(
            beneficiary_pkh.payload,
            to_address(beneficiary_address),
            orderbook.Token(buy_token[0].payload, buy_token[1].payload),
            orderbook.Token(sell_token[0].payload, sell_token[1].payload),
            1,
            orderbook.FinitePOSIXTime(int(datetime.datetime.now().timestamp() * 1000)),
            return_reward,
            min_utxo,
            advanced_features,
            did_requirements,
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

    # Set a reasonable minimum fee to work around pycardano fee estimation bug
    # The issue is that pycardano 0.9.0 doesn't properly account for datum size
    builder.fee = 500_000  # 0.5 ADA should cover most transactions
    
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
