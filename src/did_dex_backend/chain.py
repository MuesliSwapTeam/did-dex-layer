from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from . import config, database


class ChainUnavailable(RuntimeError):
    pass


PREPROD_ADDRESS_ERROR = (
    "This interface only supports Cardano Preprod payment addresses. "
    "Switch your wallet network to Preprod and reconnect."
)
LEGACY_CONTRACT_MARKER = "".join(("ata", "la"))


def _lazy_chain():
    try:
        import pycardano
        from orderbook.on_chain import orderbook
        from orderbook.off_chain.utils.contracts import get_contract
        from orderbook.off_chain.utils.from_script_context import from_address
        from orderbook.off_chain.utils.network import context
    except Exception as exc:  # pragma: no cover - depends on Cardano toolchain
        raise ChainUnavailable(str(exc)) from exc
    if context is None:
        raise ChainUnavailable("No Cardano chain context is configured.")
    return pycardano, orderbook, get_contract, from_address, context


def _parse_preprod_payment_address(wallet_address: str):
    try:
        import pycardano
    except Exception as exc:  # pragma: no cover - depends on Cardano toolchain
        raise ChainUnavailable(str(exc)) from exc

    try:
        address = pycardano.Address.from_primitive(wallet_address)
    except Exception as exc:
        raise ValueError(PREPROD_ADDRESS_ERROR) from exc

    if address.network != pycardano.Network.TESTNET or address.payment_part is None:
        raise ValueError(PREPROD_ADDRESS_ERROR)
    return address


def _invalid_address_from_provider(exc: Exception) -> bool:
    text = str(exc)
    return "Invalid address for this network" in text or "malformed address format" in text


def _public_error(exc: Exception) -> str:
    detail = str(exc)
    if LEGACY_CONTRACT_MARKER in detail.lower():
        return "Cardano chain context is not available."
    return detail


def parse_ref(ref: str) -> tuple[str, int]:
    try:
        tx_id, index = ref.split("#", 1)
        parsed_index = int(index)
    except ValueError as exc:
        raise ValueError("Invalid order reference. Expected '<tx_hash>#<index>'.") from exc
    if len(tx_id) != 64 or parsed_index < 0:
        raise ValueError("Invalid order reference. Expected '<tx_hash>#<index>'.")
    return tx_id, parsed_index


def address_from_string(address: str):
    pycardano, *_ = _lazy_chain()
    return pycardano.Address.from_primitive(address)


def payment_pkh_hex(address: str) -> str:
    addr = address_from_string(address)
    return addr.payment_part.payload.hex()


def has_wallet_did(wallet_address: str) -> bool:
    address = _parse_preprod_payment_address(wallet_address)
    pycardano, *_rest, context = _lazy_chain()
    policy = pycardano.ScriptHash.from_primitive(bytes.fromhex(config.DID_POLICY_ID))
    for utxo in context.utxos(address):
        assets = utxo.output.amount.multi_asset.get(policy)
        if assets and any(amount > 0 for amount in assets.values()):
            return True
    return False


def token_balances(wallet_address: str, pair_id: str = "muesli-swap") -> dict:
    pycardano, *_rest, context = _lazy_chain()
    pair = config.get_pair(pair_id)
    address = pycardano.Address.from_primitive(wallet_address)
    base_policy = None if pair.base.is_lovelace else pycardano.ScriptHash(bytes.fromhex(pair.base.policy_id))
    base_name = None if pair.base.is_lovelace else pycardano.AssetName(bytes.fromhex(pair.base.asset_name))
    quote_policy = None if pair.quote.is_lovelace else pycardano.ScriptHash(bytes.fromhex(pair.quote.policy_id))
    quote_name = None if pair.quote.is_lovelace else pycardano.AssetName(bytes.fromhex(pair.quote.asset_name))
    base_amount = 0
    quote_amount = 0
    for utxo in context.utxos(address):
        assets = utxo.output.amount.multi_asset
        if pair.base.is_lovelace:
            base_amount += utxo.output.amount.coin
        else:
            base_amount += assets.get(base_policy, {}).get(base_name, 0)
        if pair.quote.is_lovelace:
            quote_amount += utxo.output.amount.coin
        else:
            quote_amount += assets.get(quote_policy, {}).get(quote_name, 0)
    return {
        "walletAddress": wallet_address,
        "pairId": pair_id,
        "base": {
            **pair.base.__dict__,
            "amount": base_amount,
        },
        "quote": {
            **pair.quote.__dict__,
            "amount": quote_amount,
        },
        "hasBase": base_amount > 0,
        "hasQuote": quote_amount > 0,
    }


def did_status(wallet_address: str, registration: Optional[dict] = None) -> dict:
    try:
        has_did = has_wallet_did(wallet_address)
        address_valid = True
        chain_available = True
        error = None
    except ValueError as exc:
        has_did = False
        address_valid = False
        chain_available = True
        error = str(exc)
    except Exception as exc:
        has_did = False
        address_valid = not _invalid_address_from_provider(exc)
        chain_available = not address_valid
        error = PREPROD_ADDRESS_ERROR if not address_valid else _public_error(exc)
    return {
        "walletAddress": wallet_address,
        "hasDid": has_did,
        "policyId": config.DID_POLICY_ID,
        "registration": registration,
        "addressValid": address_valid,
        "chainAvailable": chain_available,
        "error": error,
    }


def transaction_time(tx_hash: str) -> str | None:
    try:
        *_rest, context = _lazy_chain()
        tx = context.api.transaction(tx_hash)
        block_time = getattr(tx, "block_time", None)
        if block_time is None:
            return None
        return datetime.fromtimestamp(int(block_time), timezone.utc).isoformat()
    except Exception:
        return None


def _token_amount(value: Any, token: Any) -> int:
    if token.policy_id == b"" and token.token_name == b"":
        return value.coin
    pycardano, *_ = _lazy_chain()
    policy = pycardano.ScriptHash(token.policy_id)
    name = pycardano.AssetName(token.token_name)
    return value.multi_asset.get(policy, {}).get(name, 0)


def _order_ref(utxo: Any) -> str:
    return f"{utxo.input.transaction_id}#{utxo.input.index}"


def list_orders(pair_id: str = "muesli-swap") -> list[dict]:
    pycardano, orderbook, get_contract, from_address, context = _lazy_chain()
    pair = config.get_pair(pair_id)
    _, _, orderbook_address = get_contract("orderbook", False, context)
    orders: list[dict] = []

    for utxo in context.utxos(orderbook_address):
        datum_cbor = getattr(utxo.output.datum, "cbor", None)
        if datum_cbor is None:
            continue
        try:
            datum = orderbook.Order.from_cbor(datum_cbor)
        except Exception:
            continue

        buy_unit = datum.params.buy.policy_id.hex() + datum.params.buy.token_name.hex()
        sell_unit = datum.params.sell.policy_id.hex() + datum.params.sell.token_name.hex()
        base_unit = pair.base.unit
        quote_unit = pair.quote.unit
        if {buy_unit, sell_unit} != {base_unit, quote_unit}:
            continue

        sell_remaining = _token_amount(utxo.output.amount, datum.params.sell)
        if datum.params.sell.policy_id == b"" and datum.params.sell.token_name == b"":
            sell_remaining -= datum.params.min_utxo + datum.batch_reward
        buy_remaining = datum.buy_amount
        if sell_remaining <= 0 or buy_remaining <= 0:
            continue
        side = "sell_base" if sell_unit == base_unit else "sell_quote"
        price = (
            buy_remaining / sell_remaining
            if side == "sell_base"
            else sell_remaining / buy_remaining
        )

        owner_address = str(from_address(datum.params.owner_address))
        orders.append(
            {
                "ref": _order_ref(utxo),
                "pairId": pair_id,
                "ownerAddress": owner_address,
                "side": side,
                "sellUnit": sell_unit,
                "buyUnit": buy_unit,
                "sellAmount": sell_remaining,
                "buyAmount": buy_remaining,
                "price": price,
                "batchReward": datum.batch_reward,
                "allowPartial": datum.params.allow_partial == 1,
            }
        )
    return sorted(orders, key=lambda item: (item["side"], item["price"]))


def _trade_row_to_api(row: dict) -> dict:
    return {
        "txHash": row["tx_hash"],
        "orderRef": row["order_ref"],
        "pairId": row["pair_id"],
        "makerAddress": row["maker_address"],
        "takerAddress": row["taker_address"],
        "side": row["side"],
        "price": row["price"],
        "amount": row["amount"],
        "quoteAmount": row["quote_amount"],
        "time": row["created_at"],
    }


def list_trades(pair_id: str = "muesli-swap", limit: int = 50) -> list[dict]:
    return [_trade_row_to_api(row) for row in database.list_trade_fills(pair_id, limit)]


def analytics(pair_id: str = "muesli-swap") -> dict:
    orders = list_orders(pair_id)
    bids = [o for o in orders if o["side"] == "sell_quote"]
    asks = [o for o in orders if o["side"] == "sell_base"]
    best_bid = max([o["price"] for o in bids], default=None)
    best_ask = min([o["price"] for o in asks], default=None)
    spread = None
    if best_bid is not None and best_ask is not None:
        spread = best_ask - best_bid
    recent_fills = list_trades(pair_id, limit=50)
    history = [
        {"time": fill["time"], "price": fill["price"], "volume": fill["amount"]}
        for fill in reversed(recent_fills)
    ]
    cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
    fills_24h = []
    for fill in recent_fills:
        try:
            timestamp = datetime.fromisoformat(fill["time"])
        except ValueError:
            continue
        if timestamp >= cutoff:
            fills_24h.append(fill)
    volume_24h = sum(fill["amount"] for fill in fills_24h)
    trade_count_24h = len(fills_24h)
    return {
        "pairId": pair_id,
        "depth": {
            "bids": [{"price": o["price"], "amount": o["buyAmount"]} for o in bids],
            "asks": [{"price": o["price"], "amount": o["sellAmount"]} for o in asks],
        },
        "spread": spread,
        "recentFills": recent_fills,
        "history": history,
        "volume24h": volume_24h,
        "tradeCount24h": trade_count_24h,
    }
