import click
from pycardano import (
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

from orderbook.off_chain.utils.keys import get_signing_info, get_address
from orderbook.off_chain.utils.contracts import get_contract
from orderbook.off_chain.utils.network import show_tx, context
from pycardano import Network


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
    builder = CustomTransactionBuilder(context)
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
