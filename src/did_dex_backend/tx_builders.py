from __future__ import annotations

import datetime
from typing import Any

from . import config
from .chain import ChainUnavailable, parse_ref


def _lazy_tx():
    try:
        import pycardano
        from pycardano import (
            AlonzoMetadata,
            Asset,
            AssetName,
            AuxiliaryData,
            Metadata,
            MultiAsset,
            Redeemer,
            ScriptHash,
            TransactionOutput,
            Value,
        )
        from auth_nft_minting_tool.onchain import atala_did_nft
        from orderbook.on_chain import orderbook
        from orderbook.off_chain.util import sorted_utxos
        from orderbook.off_chain.utils.contracts import find_reference_utxo, get_contract
        from orderbook.off_chain.utils.from_script_context import from_address
        from orderbook.off_chain.utils.keys import get_signing_info
        from orderbook.off_chain.utils.network import context, network
        from orderbook.off_chain.utils.to_script_context import to_address, to_tx_out_ref
        from orderbook.off_chain.utils.transaction_builder import TransactionBuilder
    except Exception as exc:  # pragma: no cover - depends on Cardano toolchain
        raise ChainUnavailable(str(exc)) from exc
    if context is None:
        raise ChainUnavailable("No Cardano chain context is configured.")
    return {
        "pycardano": pycardano,
        "AlonzoMetadata": AlonzoMetadata,
        "Asset": Asset,
        "AssetName": AssetName,
        "AuxiliaryData": AuxiliaryData,
        "Metadata": Metadata,
        "MultiAsset": MultiAsset,
        "Redeemer": Redeemer,
        "ScriptHash": ScriptHash,
        "TransactionOutput": TransactionOutput,
        "Value": Value,
        "atala_did_nft": atala_did_nft,
        "orderbook": orderbook,
        "sorted_utxos": sorted_utxos,
        "find_reference_utxo": find_reference_utxo,
        "get_contract": get_contract,
        "from_address": from_address,
        "get_signing_info": get_signing_info,
        "context": context,
        "network": network,
        "to_address": to_address,
        "to_tx_out_ref": to_tx_out_ref,
        "TransactionBuilder": TransactionBuilder,
    }


def _tx_hex(tx: Any) -> str:
    raw = tx.to_cbor()
    if isinstance(raw, bytes):
        return raw.hex()
    return raw


def _build_unsigned(deps: dict, builder: Any, change_address: Any) -> Any:
    body = builder.build(
        change_address=change_address,
        auto_ttl_offset=1000,
        auto_validity_start_offset=0,
    )
    witness_set = builder.build_witness_set()
    return deps["pycardano"].Transaction(
        body,
        witness_set,
        auxiliary_data=builder.auxiliary_data,
    )


def _add_required_signer(builder: Any, signer: Any) -> None:
    signers = list(builder.required_signers or [])
    if signer not in signers:
        signers.append(signer)
    builder.required_signers = signers


def build_did_mint_transaction(registration: dict, extra_signing_keys: list[Any] | None = None) -> Any:
    deps = _lazy_tx()
    pycardano = deps["pycardano"]
    issuer_vkey, issuer_skey, _ = deps["get_signing_info"](
        config.ISSUER_KEY_NAME, network=deps["network"]
    )
    wallet_address = pycardano.Address.from_primitive(registration["wallet_address"])
    recipient_pkh = wallet_address.payment_part.payload

    did_script, did_policy = _load_did_contract(deps)
    asset_name = deps["AssetName"](bytes.fromhex(registration["asset_name"]))
    minted = deps["MultiAsset"]({did_policy: deps["Asset"]({asset_name: 1})})

    builder = deps["TransactionBuilder"](deps["context"])
    builder.fee_buffer = 600_000
    builder.add_input_address(wallet_address)
    _add_required_signer(builder, issuer_vkey.hash())
    _add_required_signer(builder, wallet_address.payment_part)
    builder.auxiliary_data = deps["AuxiliaryData"](
        data=deps["AlonzoMetadata"](
            metadata=deps["Metadata"]({674: {"msg": ["Mint DID DEX credential"]}})
        )
    )
    redeemer = deps["Redeemer"](
        deps["atala_did_nft"].MintDID(recipient_pkh, bytes(asset_name))
    )
    builder.add_minting_script(did_script, redeemer)
    builder.mint = minted
    builder.add_output(
        deps["TransactionOutput"](
            address=wallet_address,
            amount=deps["Value"](coin=2_000_000, multi_asset=minted),
        )
    )
    signing_keys = [issuer_skey]
    if extra_signing_keys:
        signing_keys.extend(extra_signing_keys)
    return builder.build_and_sign(
        signing_keys=signing_keys,
        change_address=wallet_address,
        auto_ttl_offset=1000,
        auto_validity_start_offset=0,
    )


def build_did_mint_tx(registration: dict) -> dict:
    deps = _lazy_tx()
    tx = build_did_mint_transaction(registration)
    _, did_policy = _load_did_contract(deps)
    asset_name = deps["AssetName"](bytes.fromhex(registration["asset_name"]))
    return {"cborHex": _tx_hex(tx), "policyId": str(did_policy), "assetName": bytes(asset_name).hex()}


def _load_did_contract(deps: dict):
    script_path = config.DID_BUILD_DIR / "script.cbor"
    cbor_hex = script_path.read_text().strip()
    script = deps["pycardano"].PlutusV2Script(bytes.fromhex(cbor_hex))
    policy = deps["pycardano"].plutus_script_hash(script)
    return script, policy


def _pair_tokens(deps: dict, pair_id: str, side: str):
    pair = config.get_pair(pair_id)
    pycardano = deps["pycardano"]
    def token(asset: config.AssetConfig):
        policy_bytes = bytes.fromhex(asset.policy_id)
        name_bytes = bytes.fromhex(asset.asset_name)
        if asset.is_lovelace:
            return None, None, policy_bytes, name_bytes
        return (
            pycardano.ScriptHash(policy_bytes),
            pycardano.AssetName(name_bytes),
            policy_bytes,
            name_bytes,
        )

    base = token(pair.base)
    quote = token(pair.quote)
    if side == "sell_base":
        return base, quote
    return quote, base


def _token_to_orderbook(orderbook: Any, token: tuple[Any, Any, bytes, bytes]) -> Any:
    return orderbook.Token(token[2], token[3])


def _is_lovelace_token(token: tuple[Any, Any, bytes, bytes]) -> bool:
    return token[2] == b"" and token[3] == b""


def _asset_value(deps: dict, token: tuple[Any, Any, bytes, bytes], amount: int, coin: int = 0) -> Any:
    if _is_lovelace_token(token):
        return deps["Value"](coin=coin + amount)
    return deps["Value"](
        coin=coin,
        multi_asset=deps["MultiAsset"]({token[0]: deps["Asset"]({token[1]: amount})}),
    )


def build_test_token_mint_tx(request: Any, as_transaction: bool = False) -> Any:
    deps = _lazy_tx()
    pycardano = deps["pycardano"]
    payment_address = pycardano.Address.from_primitive(request.walletAddress)
    pair = config.get_pair(request.pairId)
    free_minting_script, free_minting_policy, _ = deps["get_contract"](
        "free_mint", False, deps["context"]
    )
    mint_assets = {}
    if not pair.base.is_lovelace:
        mint_assets[deps["AssetName"](bytes.fromhex(pair.base.asset_name))] = request.baseAmount
    if not pair.quote.is_lovelace:
        mint_assets[deps["AssetName"](bytes.fromhex(pair.quote.asset_name))] = request.quoteAmount
    if not mint_assets:
        raise ValueError("Selected pair does not contain mintable test tokens")
    mint = deps["MultiAsset"]({free_minting_policy: deps["Asset"](mint_assets)})

    builder = deps["TransactionBuilder"](deps["context"])
    builder.fee_buffer = 700_000
    builder.add_input_address(payment_address)
    _add_required_signer(builder, payment_address.payment_part)
    builder.auxiliary_data = deps["AuxiliaryData"](
        data=deps["AlonzoMetadata"](
            metadata=deps["Metadata"](
                {
                    674: {
                        "msg": [
                            f"Mint DID DEX test tokens {pair.base.ticker}/{pair.quote.ticker}"
                        ]
                    }
                }
            )
        )
    )
    builder.add_minting_script(free_minting_script, deps["Redeemer"](0))
    builder.mint = mint
    builder.add_output(
        deps["TransactionOutput"](
            address=payment_address,
            amount=deps["Value"](coin=2_000_000, multi_asset=mint),
        )
    )
    tx = _build_unsigned(deps, builder, payment_address)
    if as_transaction:
        return tx
    return {
        "cborHex": _tx_hex(tx),
        "policyId": str(free_minting_policy),
        "base": {"assetName": pair.base.asset_name, "amount": 0 if pair.base.is_lovelace else request.baseAmount},
        "quote": {"assetName": pair.quote.asset_name, "amount": 0 if pair.quote.is_lovelace else request.quoteAmount},
    }


def _unit(policy_id: bytes, token_name: bytes) -> str:
    return policy_id.hex() + token_name.hex()


def _fill_event(deps: dict, request: Any, datum: Any, sell_amount: int) -> dict:
    pair_id = getattr(request, "pairId", "muesli-swap")
    pair = config.get_pair(pair_id)
    sell_unit = _unit(datum.params.sell.policy_id, datum.params.sell.token_name)
    base_unit = pair.base.unit
    quote_unit = pair.quote.unit
    if sell_unit == base_unit:
        side = "sell_base"
        base_amount = sell_amount
        quote_amount = datum.buy_amount
    elif sell_unit == quote_unit:
        side = "sell_quote"
        base_amount = datum.buy_amount
        quote_amount = sell_amount
    else:
        raise ValueError("Order tokens do not match the requested pair")
    if base_amount <= 0 or quote_amount <= 0:
        raise ValueError("Trade amounts must be positive")
    return {
        "type": "fill",
        "pairId": pair_id,
        "orderRef": request.orderRef,
        "makerAddress": str(deps["from_address"](datum.params.owner_address)),
        "takerAddress": request.walletAddress,
        "side": side,
        "price": quote_amount / base_amount,
        "amount": base_amount,
        "quoteAmount": quote_amount,
    }


def build_place_order_tx(request: Any, as_transaction: bool = False) -> Any:
    deps = _lazy_tx()
    orderbook = deps["orderbook"]
    pycardano = deps["pycardano"]
    payment_address = pycardano.Address.from_primitive(request.walletAddress)
    sell_token, buy_token = _pair_tokens(deps, request.pairId, request.side)
    _, _, orderbook_address = deps["get_contract"]("orderbook", False, deps["context"])

    now_ms = int(datetime.datetime.now(datetime.timezone.utc).timestamp() * 1000)
    expiry = now_ms + config.DEFAULT_ORDER_TTL_MS
    params = orderbook.OrderParams(
        payment_address.payment_part.payload,
        deps["to_address"](payment_address),
        _token_to_orderbook(orderbook, buy_token),
        _token_to_orderbook(orderbook, sell_token),
        1 if request.allowPartial else 0,
        orderbook.FinitePOSIXTime(expiry),
        config.RETURN_REWARD,
        config.MIN_UTXO,
    )
    datum = orderbook.Order(params, request.buyAmount, orderbook.Nothing(), config.BATCH_REWARD)

    builder = deps["TransactionBuilder"](deps["context"])
    builder.fee_buffer = 900_000
    builder.add_input_address(payment_address)
    _add_required_signer(builder, payment_address.payment_part)
    builder.auxiliary_data = deps["AuxiliaryData"](
        data=deps["AlonzoMetadata"](
            metadata=deps["Metadata"]({674: {"msg": ["DID DEX Place Order"]}})
        )
    )
    builder.add_output(
        deps["TransactionOutput"](
            address=orderbook_address,
            amount=_asset_value(
                deps,
                sell_token,
                request.sellAmount,
                coin=config.MIN_UTXO + config.BATCH_REWARD,
            ),
            datum=datum,
        )
    )
    tx = _build_unsigned(deps, builder, payment_address)
    if as_transaction:
        return tx
    return {"cborHex": _tx_hex(tx)}


def _find_order(deps: dict, ref: str):
    tx_id, index = parse_ref(ref)
    _, _, orderbook_address = deps["get_contract"]("orderbook", False, deps["context"])
    for utxo in deps["context"].utxos(orderbook_address):
        if str(utxo.input.transaction_id) == tx_id and utxo.input.index == index:
            datum_cbor = getattr(utxo.output.datum, "cbor", None)
            if datum_cbor is None:
                raise ValueError("Order UTxO has no inline order datum")
            datum = deps["orderbook"].Order.from_cbor(datum_cbor)
            return utxo, datum
    raise ValueError("Order UTxO not found")


def _wallet_inputs(
    deps: dict,
    wallet_address: Any,
    required_token: tuple[Any, Any] | None = None,
    required_amount: int = 0,
):
    policy = deps["ScriptHash"].from_primitive(bytes.fromhex(config.DID_POLICY_ID))
    utxos = deps["context"].utxos(wallet_address)
    did = None
    fee = None
    token_inputs = []
    token_total = 0
    for utxo in utxos:
        if did is None and utxo.output.amount.multi_asset.get(policy):
            did = utxo
        if fee is None and len(utxo.output.amount.multi_asset) == 0:
            fee = utxo
        if required_token is not None:
            if _is_lovelace_token(required_token):
                amount = utxo.output.amount.coin
            else:
                amount = utxo.output.amount.multi_asset.get(required_token[0], {}).get(
                    required_token[1], 0
                )
            if amount > 0:
                token_inputs.append(utxo)
                token_total += amount
    if did is None:
        raise ValueError("Wallet does not hold the required DID NFT")
    selected = [did]
    if fee is not None and fee != did:
        selected.append(fee)
    if required_token is not None:
        if token_total < required_amount:
            raise ValueError("Wallet does not have enough fill token for this order")
        for utxo in token_inputs:
            if utxo not in selected:
                selected.append(utxo)
    return selected


def build_cancel_order_tx(request: Any, as_transaction: bool = False) -> Any:
    deps = _lazy_tx()
    orderbook = deps["orderbook"]
    pycardano = deps["pycardano"]
    payment_address = pycardano.Address.from_primitive(request.walletAddress)
    order_utxo, datum = _find_order(deps, request.orderRef)
    user_inputs = _wallet_inputs(deps, payment_address)
    all_inputs_sorted = deps["sorted_utxos"](user_inputs + [order_utxo])
    order_input_index = all_inputs_sorted.index(order_utxo)
    redeemer = deps["Redeemer"](orderbook.CancelOrder(order_input_index))
    orderbook_script, _, _ = deps["get_contract"]("orderbook", False, deps["context"])

    builder = deps["TransactionBuilder"](deps["context"])
    builder.fee_buffer = 1_500_000
    _add_required_signer(builder, payment_address.payment_part)
    for utxo in user_inputs:
        builder.add_input(utxo)
    builder.add_script_input(order_utxo, script=orderbook_script, datum=None, redeemer=redeemer)
    builder.add_output(deps["TransactionOutput"](address=payment_address, amount=order_utxo.output.amount))
    tx = _build_unsigned(deps, builder, payment_address)
    if as_transaction:
        return tx
    return {"cborHex": _tx_hex(tx)}


def build_fill_order_tx(request: Any, as_transaction: bool = False) -> Any:
    deps = _lazy_tx()
    orderbook = deps["orderbook"]
    pycardano = deps["pycardano"]
    payment_address = pycardano.Address.from_primitive(request.walletAddress)
    order_utxo, datum = _find_order(deps, request.orderRef)
    owner_address = str(deps["from_address"](datum.params.owner_address))
    if owner_address == request.walletAddress:
        raise ValueError("Cannot fill your own order; cancel it instead.")
    fill_amount = request.fillAmount or datum.buy_amount
    if fill_amount != datum.buy_amount:
        raise ValueError("Partial fills are not exposed by the v1 backend.")

    buy_token = (
        None if datum.params.buy.policy_id == b"" else pycardano.ScriptHash(datum.params.buy.policy_id),
        None if datum.params.buy.policy_id == b"" else pycardano.AssetName(datum.params.buy.token_name),
        datum.params.buy.policy_id,
        datum.params.buy.token_name,
    )
    user_inputs = _wallet_inputs(deps, payment_address, buy_token, datum.buy_amount)
    all_inputs_sorted = deps["sorted_utxos"](user_inputs + [order_utxo])
    order_input_index = all_inputs_sorted.index(order_utxo)
    order_output_index = 0
    redeemer = deps["Redeemer"](orderbook.FullMatch(order_input_index, order_output_index))
    orderbook_script, _, orderbook_address = deps["get_contract"]("orderbook", False, deps["context"])

    sell_token = (
        None if datum.params.sell.policy_id == b"" else pycardano.ScriptHash(datum.params.sell.policy_id),
        None if datum.params.sell.policy_id == b"" else pycardano.AssetName(datum.params.sell.token_name),
        datum.params.sell.policy_id,
        datum.params.sell.token_name,
    )
    if _is_lovelace_token(sell_token):
        sell_amount = order_utxo.output.amount.coin - datum.params.min_utxo - datum.batch_reward
    else:
        sell_amount = order_utxo.output.amount.multi_asset.get(sell_token[0], {}).get(sell_token[1], 0)
    event = _fill_event(deps, request, datum, sell_amount)
    sell_asset = _asset_value(deps, sell_token, sell_amount)
    buy_asset = _asset_value(deps, buy_token, datum.buy_amount)
    return_value = order_utxo.output.amount - datum.batch_reward - sell_asset + buy_asset
    full_datum = orderbook.Order(
        datum.params,
        0,
        deps["to_tx_out_ref"](order_utxo.input),
        0,
    )

    builder = deps["TransactionBuilder"](deps["context"])
    builder.fee_buffer = 1_500_000
    _add_required_signer(builder, payment_address.payment_part)
    for utxo in user_inputs:
        builder.add_input(utxo)
    builder.add_script_input(order_utxo, script=orderbook_script, datum=None, redeemer=redeemer)
    builder.add_output(
        deps["TransactionOutput"](
            address=orderbook_address,
            amount=return_value,
            datum=full_datum,
        )
    )
    builder.add_output(
        deps["TransactionOutput"](
            address=payment_address,
            amount=sell_asset
            if _is_lovelace_token(sell_token)
            else deps["Value"](coin=2_000_000, multi_asset=sell_asset.multi_asset),
        )
    )
    tx = _build_unsigned(deps, builder, payment_address)
    if as_transaction:
        return tx
    return {"cborHex": _tx_hex(tx), "event": event}
