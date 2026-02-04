import click
from pycardano import (
    Redeemer,
    AuxiliaryData,
    AlonzoMetadata,
    Metadata,
    TransactionOutput,
    MultiAsset,
    Value,
    AssetName,
    Asset,
    Network,
)

from orderbook.off_chain.utils.keys import get_signing_info, get_address
from orderbook.off_chain.utils.contracts import get_contract
from orderbook.off_chain.utils.network import show_tx, context
from orderbook.off_chain.utils.transaction_builder import TransactionBuilder


@click.command()
@click.argument("name")
@click.option(
    "--token-name",
    type=str,
    default="muesli",
    help="Name of tokens to mint",
)
@click.option(
    "--amount",
    type=int,
    default=1_000_000,
    help="Amount of tokens to mint",
)
def main(
    name: str,
    token_name: str,
    amount: int,
):
    free_minting_contract_script, free_minting_contract_hash, _ = get_contract(
        "free_mint", False, context
    )

    # Get signing info (includes payment address)
    payment_vkey, payment_skey, payment_address = get_signing_info(
        name, network=Network.TESTNET
    )

    # Build the transaction
    # Use standard TransactionBuilder with increased fee buffer to account for:
    # - Minting script execution
    # - Transaction size estimation variance
    builder = TransactionBuilder(context)
    builder.fee_buffer = 600_000  # Add 0.6 ADA buffer for minting operations
    builder.auxiliary_data = AuxiliaryData(
        data=AlonzoMetadata(metadata=Metadata({674: {"msg": [f"Mint {token_name}"]}}))
    )
    builder.add_input_address(payment_address)
    builder.add_minting_script(free_minting_contract_script, Redeemer(0))
    mint = MultiAsset(
        {free_minting_contract_hash: Asset({AssetName(token_name.encode()): amount})}
    )
    builder.add_output(
        TransactionOutput(
            address=payment_address,
            amount=Value(coin=2000000, multi_asset=mint),
        )
    )
    builder.mint = mint

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
