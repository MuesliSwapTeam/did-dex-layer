"""
Debugging tools for the MuesliSwap DID Orderbook system.

This module provides comprehensive debugging utilities for smart contracts,
DID authentication, and orderbook operations.
"""

import json
import time
import traceback
from typing import Dict, Any, List, Optional, Union
from datetime import datetime, timedelta
import pycardano
from pycardano import (
    Transaction,
    TransactionBuilder,
    TransactionOutput,
    Value,
    MultiAsset,
    Asset,
)

from orderbook.on_chain import orderbook
from orderbook.off_chain.utils.network import context, network
from orderbook.off_chain.utils.keys import get_signing_info, get_address
from orderbook.off_chain.utils.contracts import get_contract
from orderbook.off_chain.utils.to_script_context import to_address


class OrderbookDebugger:
    """Debugging tools for orderbook operations."""

    def __init__(self):
        self.orderbook_script, _, self.orderbook_address = get_contract(
            "orderbook", False
        )
        self.free_mint_script, self.free_mint_hash, _ = get_contract("free_mint", False)
        self.debug_log = []
        self.performance_metrics = {}

    def debug_order_creation(
        self, trader_name: str, order_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Debug order creation process."""
        print(f"Debugging order creation for {trader_name}")

        debug_info = {
            "trader_name": trader_name,
            "timestamp": datetime.now().isoformat(),
            "steps": [],
            "errors": [],
            "warnings": [],
        }

        try:
            # Step 1: Validate trader
            debug_info["steps"].append("Validating trader...")
            trader = self.validate_trader(trader_name)
            debug_info["trader_info"] = {
                "address": str(trader["address"]),
                "has_skey": trader["skey"] is not None,
            }

            # Step 2: Validate order data
            debug_info["steps"].append("Validating order data...")
            validation_result = self.validate_order_data(order_data)
            debug_info["validation"] = validation_result

            if not validation_result["valid"]:
                debug_info["errors"].extend(validation_result["errors"])
                return debug_info

            # Step 3: Create order parameters
            debug_info["steps"].append("Creating order parameters...")
            order_params = self.create_order_parameters(trader, order_data)
            debug_info["order_params"] = {
                "owner_pkh": str(order_params.owner_pkh),
                "buy_token": str(order_params.buy),
                "sell_token": str(order_params.sell),
                "allow_partial": order_params.allow_partial,
                "expiry_date": str(order_params.expiry_date),
                "return_reward": order_params.return_reward,
                "min_utxo": order_params.min_utxo,
            }

            # Step 4: Create order
            debug_info["steps"].append("Creating order...")
            order = orderbook.Order(
                order_params,
                order_data["buy_amount"],
                orderbook.Nothing(),
                order_data.get("batch_reward", 1000000),
            )
            debug_info["order_created"] = True

            # Step 5: Validate order
            debug_info["steps"].append("Validating created order...")
            order_validation = self.validate_order(order)
            debug_info["order_validation"] = order_validation

            debug_info["success"] = True
            print("✅ Order creation debug completed successfully")

        except Exception as e:
            debug_info["errors"].append(f"Order creation failed: {str(e)}")
            debug_info["traceback"] = traceback.format_exc()
            print(f"❌ Order creation debug failed: {e}")

        self.debug_log.append(debug_info)
        return debug_info

    def debug_order_matching(self, orders: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Debug order matching process."""
        print(f"🔍 Debugging order matching for {len(orders)} orders")

        debug_info = {
            "timestamp": datetime.now().isoformat(),
            "total_orders": len(orders),
            "matches_found": 0,
            "matching_pairs": [],
            "errors": [],
            "performance": {},
        }

        start_time = time.time()

        try:
            # Analyze order compatibility
            debug_info["steps"] = []
            debug_info["steps"].append("Analyzing order compatibility...")

            compatible_pairs = self.find_compatible_orders(orders)
            debug_info["compatible_pairs"] = len(compatible_pairs)

            # Test matching logic
            debug_info["steps"].append("Testing matching logic...")
            for i, (order1, order2) in enumerate(compatible_pairs):
                match_result = self.test_order_match(order1, order2)
                if match_result["can_match"]:
                    debug_info["matches_found"] += 1
                    debug_info["matching_pairs"].append(
                        {
                            "order1_id": order1.get("id", f"order_{i}_1"),
                            "order2_id": order2.get("id", f"order_{i}_2"),
                            "match_amount": match_result["match_amount"],
                            "match_price": match_result["match_price"],
                        }
                    )

            debug_info["performance"]["matching_time"] = time.time() - start_time
            debug_info["success"] = True
            print(
                f"✅ Order matching debug completed: {debug_info['matches_found']} matches found"
            )

        except Exception as e:
            debug_info["errors"].append(f"Order matching failed: {str(e)}")
            debug_info["traceback"] = traceback.format_exc()
            print(f"❌ Order matching debug failed: {e}")

        self.debug_log.append(debug_info)
        return debug_info

    def debug_did_authentication(self, user_did: str, challenge: str) -> Dict[str, Any]:
        """Debug DID authentication process."""
        print(f"🔍 Debugging DID authentication for {user_did}")

        debug_info = {
            "user_did": user_did,
            "timestamp": datetime.now().isoformat(),
            "steps": [],
            "errors": [],
            "warnings": [],
        }

        try:
            # Step 1: Validate DID format
            debug_info["steps"].append("Validating DID format...")
            did_validation = self.validate_did_format(user_did)
            debug_info["did_validation"] = did_validation

            if not did_validation["valid"]:
                debug_info["errors"].extend(did_validation["errors"])
                return debug_info

            # Step 2: Check challenge validity
            debug_info["steps"].append("Checking challenge validity...")
            challenge_validation = self.validate_challenge(challenge)
            debug_info["challenge_validation"] = challenge_validation

            # Step 3: Simulate NFT validation
            debug_info["steps"].append("Simulating NFT validation...")
            nft_validation = self.simulate_nft_validation(user_did)
            debug_info["nft_validation"] = nft_validation

            # Step 4: Test authentication flow
            debug_info["steps"].append("Testing authentication flow...")
            auth_result = self.test_authentication_flow(user_did, challenge)
            debug_info["auth_result"] = auth_result

            debug_info["success"] = auth_result["success"]
            print("✅ DID authentication debug completed successfully")

        except Exception as e:
            debug_info["errors"].append(f"DID authentication failed: {str(e)}")
            debug_info["traceback"] = traceback.format_exc()
            print(f"❌ DID authentication debug failed: {e}")

        self.debug_log.append(debug_info)
        return debug_info

    def debug_transaction_building(
        self, transaction_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Debug transaction building process."""
        print("🔍 Debugging transaction building...")

        debug_info = {
            "timestamp": datetime.now().isoformat(),
            "transaction_type": transaction_data.get("type", "unknown"),
            "steps": [],
            "errors": [],
            "warnings": [],
            "performance": {},
        }

        start_time = time.time()

        try:
            # Step 1: Validate inputs
            debug_info["steps"].append("Validating transaction inputs...")
            input_validation = self.validate_transaction_inputs(transaction_data)
            debug_info["input_validation"] = input_validation

            if not input_validation["valid"]:
                debug_info["errors"].extend(input_validation["errors"])
                return debug_info

            # Step 2: Build transaction
            debug_info["steps"].append("Building transaction...")
            builder = TransactionBuilder(context)

            # Add inputs
            for input_data in transaction_data.get("inputs", []):
                builder.add_input(input_data["utxo"])
                debug_info["steps"].append(
                    f"Added input: {input_data.get('id', 'unknown')}"
                )

            # Add outputs
            for output_data in transaction_data.get("outputs", []):
                output = TransactionOutput(
                    address=output_data["address"],
                    amount=output_data["amount"],
                    datum=output_data.get("datum"),
                )
                builder.add_output(output)
                debug_info["steps"].append(
                    f"Added output: {output_data.get('id', 'unknown')}"
                )

            # Add scripts
            for script_data in transaction_data.get("scripts", []):
                builder.add_script_input(
                    script_data["utxo"],
                    script_data["script"],
                    script_data.get("datum"),
                    script_data["redeemer"],
                )
                debug_info["steps"].append(
                    f"Added script: {script_data.get('id', 'unknown')}"
                )

            # Step 3: Build and validate
            debug_info["steps"].append("Building and validating transaction...")
            transaction = builder.build()

            debug_info["transaction_info"] = {
                "id": str(transaction.id),
                "inputs_count": len(transaction.transaction_body.inputs),
                "outputs_count": len(transaction.transaction_body.outputs),
                "fee": transaction.transaction_body.fee,
                "size": len(transaction.to_cbor()),
            }

            debug_info["performance"]["build_time"] = time.time() - start_time
            debug_info["success"] = True
            print("✅ Transaction building debug completed successfully")

        except Exception as e:
            debug_info["errors"].append(f"Transaction building failed: {str(e)}")
            debug_info["traceback"] = traceback.format_exc()
            print(f"❌ Transaction building debug failed: {e}")

        self.debug_log.append(debug_info)
        return debug_info

    def validate_trader(self, trader_name: str) -> Dict[str, Any]:
        """Validate trader information."""
        try:
            vkey, skey, address = get_signing_info(trader_name, network=network)
            return {"vkey": vkey, "skey": skey, "address": address, "valid": True}
        except Exception as e:
            return {"valid": False, "error": str(e)}

    def validate_order_data(self, order_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate order data."""
        errors = []
        warnings = []

        # Check required fields
        required_fields = ["buy_amount", "sell_amount", "price"]
        for field in required_fields:
            if field not in order_data:
                errors.append(f"Missing required field: {field}")

        # Validate amounts
        if "buy_amount" in order_data and order_data["buy_amount"] <= 0:
            errors.append("Buy amount must be positive")

        if "sell_amount" in order_data and order_data["sell_amount"] <= 0:
            errors.append("Sell amount must be positive")

        # Validate price
        if "price" in order_data and order_data["price"] <= 0:
            errors.append("Price must be positive")

        # Check for reasonable values
        if "buy_amount" in order_data and order_data["buy_amount"] > 1000000:
            warnings.append("Large buy amount detected")

        return {"valid": len(errors) == 0, "errors": errors, "warnings": warnings}

    def create_order_parameters(
        self, trader: Dict, order_data: Dict[str, Any]
    ) -> orderbook.OrderParams:
        """Create order parameters."""
        sell_token = (self.free_mint_hash, pycardano.AssetName(b"muesli"))
        buy_token = (self.free_mint_hash, pycardano.AssetName(b"swap"))

        if order_data.get("is_sell_order", False):
            sell_token, buy_token = buy_token, sell_token

        return orderbook.OrderParams(
            trader["address"].payment_part,
            to_address(trader["address"]),
            orderbook.Token(buy_token[0].payload, buy_token[1].payload),
            orderbook.Token(sell_token[0].payload, sell_token[1].payload),
            1,  # allow_partial
            orderbook.FinitePOSIXTime(
                int((datetime.now() + timedelta(hours=1)).timestamp() * 1000)
            ),
            650000,  # return_reward
            2300000,  # min_utxo
        )

    def validate_order(self, order: orderbook.Order) -> Dict[str, Any]:
        """Validate created order."""
        errors = []
        warnings = []

        # Check order structure
        if not hasattr(order, "params"):
            errors.append("Order missing parameters")

        if not hasattr(order, "buy_amount"):
            errors.append("Order missing buy amount")

        # Check buy amount
        if order.buy_amount <= 0:
            errors.append("Invalid buy amount")

        # Check expiry
        if hasattr(order.params, "expiry_date"):
            current_time = int(datetime.now().timestamp() * 1000)
            if hasattr(order.params.expiry_date, "time"):
                if order.params.expiry_date.time < current_time:
                    warnings.append("Order already expired")

        return {"valid": len(errors) == 0, "errors": errors, "warnings": warnings}

    def find_compatible_orders(self, orders: List[Dict[str, Any]]) -> List[tuple]:
        """Find compatible order pairs."""
        compatible_pairs = []

        for i, order1 in enumerate(orders):
            for j, order2 in enumerate(orders[i + 1 :], i + 1):
                if self.orders_compatible(order1, order2):
                    compatible_pairs.append((order1, order2))

        return compatible_pairs

    def orders_compatible(self, order1: Dict[str, Any], order2: Dict[str, Any]) -> bool:
        """Check if two orders are compatible."""
        # Simple compatibility check
        return order1.get("buy_token") == order2.get("sell_token") and order1.get(
            "sell_token"
        ) == order2.get("buy_token")

    def test_order_match(
        self, order1: Dict[str, Any], order2: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Test if two orders can match."""
        if not self.orders_compatible(order1, order2):
            return {"can_match": False, "reason": "Orders not compatible"}

        match_amount = min(order1.get("amount", 0), order2.get("amount", 0))
        match_price = (order1.get("price", 0) + order2.get("price", 0)) / 2

        return {
            "can_match": match_amount > 0,
            "match_amount": match_amount,
            "match_price": match_price,
        }

    def validate_did_format(self, did: str) -> Dict[str, Any]:
        """Validate DID format."""
        errors = []

        if not did.startswith("did:prism:"):
            errors.append("Invalid DID format: must start with 'did:prism:'")

        if len(did.split(":")) < 3:
            errors.append("Invalid DID format: missing components")

        return {"valid": len(errors) == 0, "errors": errors}

    def validate_challenge(self, challenge: str) -> Dict[str, Any]:
        """Validate challenge format."""
        errors = []

        if not challenge or len(challenge) < 10:
            errors.append("Challenge too short")

        if not challenge.isalnum():
            errors.append("Challenge contains invalid characters")

        return {"valid": len(errors) == 0, "errors": errors}

    def simulate_nft_validation(self, user_did: str) -> Dict[str, Any]:
        """Simulate NFT validation."""
        # Mock NFT validation
        return {
            "valid": True,
            "nft_policy_id": "672ae1e79585ad1543ef6b4b6c8989a17adcea3040f77ede128d9217",
            "nft_token_name": user_did.split(":")[-1][:32],
        }

    def test_authentication_flow(self, user_did: str, challenge: str) -> Dict[str, Any]:
        """Test complete authentication flow."""
        # Mock authentication flow
        return {
            "success": True,
            "user_did": user_did,
            "challenge_valid": True,
            "nft_valid": True,
        }

    def validate_transaction_inputs(
        self, transaction_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Validate transaction inputs."""
        errors = []

        if "inputs" not in transaction_data or not transaction_data["inputs"]:
            errors.append("No inputs provided")

        if "outputs" not in transaction_data or not transaction_data["outputs"]:
            errors.append("No outputs provided")

        return {"valid": len(errors) == 0, "errors": errors}

    def generate_debug_report(self) -> Dict[str, Any]:
        """Generate comprehensive debug report."""
        return {
            "timestamp": datetime.now().isoformat(),
            "total_debug_sessions": len(self.debug_log),
            "debug_log": self.debug_log,
            "performance_metrics": self.performance_metrics,
            "summary": {
                "successful_operations": len(
                    [log for log in self.debug_log if log.get("success", False)]
                ),
                "failed_operations": len(
                    [log for log in self.debug_log if not log.get("success", False)]
                ),
                "total_errors": sum(
                    len(log.get("errors", [])) for log in self.debug_log
                ),
            },
        }

    def save_debug_log(self, filename: str = None):
        """Save debug log to file."""
        if filename is None:
            filename = f"debug_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

        with open(filename, "w") as f:
            json.dump(self.generate_debug_report(), f, indent=2, default=str)

        print(f"📁 Debug log saved to {filename}")


def main():
    """Run debugging tools demo."""
    debugger = OrderbookDebugger()

    # Demo order creation debugging
    order_data = {
        "buy_amount": 100,
        "sell_amount": 50,
        "price": 0.5,
        "is_sell_order": False,
    }

    debugger.debug_order_creation("trader1", order_data)

    # Demo order matching debugging
    orders = [
        {
            "id": "order1",
            "buy_token": "token_a",
            "sell_token": "token_b",
            "amount": 100,
            "price": 0.5,
        },
        {
            "id": "order2",
            "buy_token": "token_b",
            "sell_token": "token_a",
            "amount": 50,
            "price": 0.6,
        },
    ]

    debugger.debug_order_matching(orders)

    # Generate and save debug report
    debugger.save_debug_log()


if __name__ == "__main__":
    main()
