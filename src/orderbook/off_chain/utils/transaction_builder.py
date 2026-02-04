"""
Transaction Builder Utilities

This module provides a TransactionBuilder that applies fee_buffer on top of
the estimated fee. PyCardano 0.9.0 (vendor wheel) does NOT support fee_buffer
natively - it ignores the attribute. We use a subclass that overrides
_estimate_fee() to add the buffer when the base class does not support it.

MIGRATION GUIDE:
===============

OLD CODE (deprecated):
    from orderbook.off_chain.utils.transaction_builder import CustomTransactionBuilder
    builder = CustomTransactionBuilder(context)
    
NEW CODE (recommended):
    from pycardano import TransactionBuilder
    builder = TransactionBuilder(context)
    builder.fee_buffer = 500_000  # Add appropriate buffer in lovelace
    
FEE BUFFER RECOMMENDATIONS (Based on Actual Production Testing):
- Simple transactions (payments, bulk): 400,000 lovelace (0.4 ADA)
- Minting operations: 500,000-600,000 lovelace (0.5-0.6 ADA)
- Order placement (with datums): 800,000 lovelace (0.8 ADA)
- Reference script deployment: 1,000,000 lovelace (1.0 ADA) for 30KB+ scripts
- Script transactions (cancel orders): 1,500,000 lovelace (1.5 ADA)
- Complex transactions (fill orders, modify): 1,500,000 lovelace (1.5 ADA)

The fee_buffer is added on top of the estimated fee to account for:
1. Reference script fees (can add significant overhead)
2. Datum size variations (especially for complex order params)
3. Transaction size estimation variance
4. Plutus script execution costs
5. Multiple script executions or minting operations

IMPORTANT: These buffers replace the 1.15x multiplier from the old CustomTransactionBuilder.
The standard estimator may underestimate fees for complex transactions, hence the higher buffers.

If you still encounter "fee too small" errors, increase the fee_buffer by 100,000-200,000 increments.
"""

from pycardano import TransactionBuilder as _BaseTransactionBuilder


def _base_supports_fee_buffer():
    """True if the base TransactionBuilder has native fee_buffer support (pycardano >= 0.10)."""
    return "fee_buffer" in getattr(_BaseTransactionBuilder, "__dataclass_fields__", {})


class TransactionBuilder(_BaseTransactionBuilder):
    """
    TransactionBuilder that applies fee_buffer when the base (e.g. pycardano 0.9.0) does not.
    Set builder.fee_buffer = N (lovelace) before build_and_sign(); the fee will be
    estimated_fee + fee_buffer. If the base already supports fee_buffer, we do not add twice.
    """

    def _estimate_fee(self):
        base_fee = super()._estimate_fee()
        if _base_supports_fee_buffer():
            return base_fee
        buffer = getattr(self, "fee_buffer", None) or 0
        return base_fee + buffer


__all__ = ["TransactionBuilder", "create_transaction_builder"]


def create_transaction_builder(context, fee_buffer=800_000):
    """
    Create a standard TransactionBuilder with appropriate fee buffer.
    
    Args:
        context: ChainContext for blockchain interaction
        fee_buffer: Additional lovelace to add to estimated fee (default: 800,000)
                   Increase for script transactions (1,500,000) or complex operations
    
    Returns:
        TransactionBuilder: Configured transaction builder
        
    Example:
        # Simple/minting transaction
        builder = create_transaction_builder(context, fee_buffer=600_000)
        
        # Order placement
        builder = create_transaction_builder(context, fee_buffer=800_000)
        
        # Script transaction (cancel/modify/fill)
        builder = create_transaction_builder(context, fee_buffer=1_500_000)
        
        builder.add_input_address(address)
        # ... add outputs, scripts, etc.
        signed_tx = builder.build_and_sign([skey], change_address=address)
    """
    builder = TransactionBuilder(context)  # our subclass that applies fee_buffer
    builder.fee_buffer = fee_buffer
    return builder
