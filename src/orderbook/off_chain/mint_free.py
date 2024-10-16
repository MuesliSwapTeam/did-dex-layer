import click
from pycardano import (
    OgmiosChainContext,
    TransactionBuilder,
    Redeemer,
    AuxiliaryData,
    AlonzoMetadata,
    Metadata,
    TransactionOutput,
    MultiAsset,
    Value,
    AssetName,
    Asset,
)

from src.orderbook.off_chain.utils.keys import get_signing_info, get_address
from src.orderbook.off_chain.utils.contracts import get_contract
from src.orderbook.off_chain.utils.network import show_tx, context
from pycardano import Network


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
        "free_mint", False
    )

    # Get payment address
    payment_address = get_address(name)

    # Build the transaction
    builder = TransactionBuilder(context)
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
    payment_vkey, payment_skey, payment_address = get_signing_info(name, network=Network.TESTNET)
    signed_tx = builder.build_and_sign(
        signing_keys=[payment_skey],
        change_address=payment_address,
    )

    # Submit the transaction
    context.submit_tx(signed_tx.to_cbor())

    show_tx(signed_tx)


if __name__ == "__main__":
    main()