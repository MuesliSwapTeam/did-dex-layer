"""
Bulk payments functionality for the MuesliSwap DID Orderbook system.

This module allows processing multiple payments in a single transaction,
reducing fees and improving efficiency for batch operations.
"""

import datetime
import json
from typing import List, Dict, Any, Optional

import click
import pycardano
from pycardano import (
    TransactionBuilder,
    TransactionOutput,
    Asset,
    AuxiliaryData,
    AlonzoMetadata,
    Metadata,
    Value,
    MultiAsset,
)

from orderbook.off_chain.utils.keys import get_signing_info, get_address, network
from orderbook.off_chain.utils.contracts import get_contract
from orderbook.off_chain.utils.network import context, show_tx
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


@click.command()
@click.argument("payer_name")
@click.option(
    "--payments-file",
    type=click.Path(exists=True),
    help="JSON file containing payment details",
)
@click.option(
    "--recipients",
    multiple=True,
    help="Recipient addresses (can be used multiple times)",
)
@click.option(
    "--amounts",
    multiple=True,
    type=int,
    help="Payment amounts in lovelace (can be used multiple times)",
)
@click.option(
    "--token-policy",
    help="Token policy ID for non-ADA payments",
)
@click.option(
    "--token-name",
    help="Token name for non-ADA payments",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Simulate the transaction without submitting",
)
def main(
    payer_name: str,
    payments_file: Optional[str] = None,
    recipients: tuple = (),
    amounts: tuple = (),
    token_policy: Optional[str] = None,
    token_name: Optional[str] = None,
    dry_run: bool = False,
):
    """
    Process bulk payments in a single transaction.

    Examples:

    # Pay ADA to multiple recipients using command line
    python -m orderbook.off_chain.bulk_payments alice --recipients addr1... --recipients addr2... --amounts 1000000 --amounts 2000000

    # Pay tokens using a JSON file
    python -m orderbook.off_chain.bulk_payments alice --payments-file payments.json --token-policy abc123... --token-name MyToken

    # Dry run to simulate without submitting
    python -m orderbook.off_chain.bulk_payments alice --payments-file payments.json --dry-run
    """

    # Get payer credentials
    payment_vkey, payment_skey, payment_address = get_signing_info(
        payer_name, network=network
    )

    # Parse payment details
    payments = []

    if payments_file:
        # Load payments from JSON file
        with open(payments_file, "r") as f:
            file_data = json.load(f)
            payments = file_data.get("payments", [])
    else:
        # Use command line arguments
        if len(recipients) != len(amounts):
            raise click.ClickException(
                "Number of recipients must match number of amounts"
            )

        for recipient, amount in zip(recipients, amounts):
            payments.append({"recipient": recipient, "amount": amount})

    if not payments:
        raise click.ClickException("No payments specified")

    print(f"Processing {len(payments)} bulk payments from {payer_name}...")

    # Build the transaction
    builder = CustomTransactionBuilder(context)
    builder.add_input_address(payment_address)

    # Add metadata
    builder.auxiliary_data = AuxiliaryData(
        data=AlonzoMetadata(
            metadata=Metadata(
                {
                    674: {"msg": ["MuesliSwap Bulk Payment"]},
                    675: {"payments_count": len(payments)},
                }
            )
        )
    )

    total_ada_amount = 0
    total_token_amount = 0

    # Process each payment
    for i, payment in enumerate(payments):
        recipient_addr = payment["recipient"]
        amount = payment["amount"]

        # Parse recipient address
        if isinstance(recipient_addr, str):
            try:
                recipient_address = pycardano.Address.from_bech32(recipient_addr)
            except:
                # Try to get address by name if it's not a bech32 address
                recipient_address = get_address(recipient_addr)
        else:
            recipient_address = recipient_addr

        # Create payment output
        if token_policy and token_name:
            # Token payment
            policy_id = pycardano.ScriptHash.from_primitive(bytes.fromhex(token_policy))
            asset_name = pycardano.AssetName(token_name.encode())

            payment_value = Value(
                coin=2000000,  # Minimum ADA for UTxO
                multi_asset=MultiAsset({policy_id: Asset({asset_name: amount})}),
            )
            total_token_amount += amount
            total_ada_amount += 2000000
        else:
            # ADA payment
            payment_value = Value(coin=amount)
            total_ada_amount += amount

        builder.add_output(
            TransactionOutput(address=recipient_address, amount=payment_value)
        )

        print(f"  Payment {i+1}: {amount} to {str(recipient_address)[:20]}...")

    print(f"Total ADA: {total_ada_amount / 1_000_000:.6f} ADA")
    if total_token_amount > 0:
        print(f"Total Tokens: {total_token_amount} {token_name or 'tokens'}")

    if dry_run:
        print("DRY RUN: Transaction not submitted")
        try:
            # Build transaction to validate
            unsigned_tx = builder.build()
            print(
                f"Transaction would have {len(unsigned_tx.transaction_body.outputs)} outputs"
            )
            print(
                f"Estimated fee: {unsigned_tx.transaction_body.fee / 1_000_000:.6f} ADA"
            )
            return
        except Exception as e:
            print(f"Transaction build failed: {e}")
            return

    # Sign and submit the transaction
    try:
        signed_tx = builder.build_and_sign(
            signing_keys=[payment_skey],
            change_address=payment_address,
        )

        # Submit the transaction
        context.submit_tx(signed_tx.to_cbor())

        show_tx(signed_tx)
        print(f"✅ Bulk payment transaction submitted successfully!")
        print(f"   Transaction ID: {signed_tx.id}")
        print(f"   Processed {len(payments)} payments")

    except Exception as e:
        print(f"❌ Bulk payment failed: {e}")
        raise


def create_payments_file(filename: str = "bulk_payments.json"):
    """Create a sample payments file."""
    sample_payments = {
        "payments": [
            {
                "recipient": "addr_test1qp...",  # Example testnet address
                "amount": 1000000,  # 1 ADA
                "note": "Payment 1",
            },
            {
                "recipient": "addr_test1qr...",  # Example testnet address
                "amount": 2000000,  # 2 ADA
                "note": "Payment 2",
            },
            {
                "recipient": "trader1",  # Can use wallet names
                "amount": 500000,  # 0.5 ADA
                "note": "Payment to trader1",
            },
        ],
        "token_policy": "optional_policy_id_here",
        "token_name": "optional_token_name_here",
        "description": "Bulk payment batch",
    }

    with open(filename, "w") as f:
        json.dump(sample_payments, f, indent=2)

    print(f"Sample payments file created: {filename}")


@click.command()
@click.option("--filename", default="bulk_payments.json", help="Output filename")
def create_sample(filename: str):
    """Create a sample bulk payments JSON file."""
    create_payments_file(filename)


if __name__ == "__main__":
    main()
