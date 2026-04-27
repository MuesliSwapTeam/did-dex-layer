"""
Orderbook with DID Layer

Features:
- Allow orders to be partially filled
- Allow orders to be cancelled
- Allow orders to be automatically returned after expiry
- Allow multiple matches by the same owner in a single transaction
- Lower fees (Plutus V2 + OpShin)
- Enforces DID Authentication NFT
- Advanced order types: Stop-loss, Minimum fill, TWAP orders
"""

from orderbook.on_chain.utils.custom_fract import *
from orderbook.on_chain.utils.ext_values import *
from orderbook.on_chain.utils.ext_interval import *
from orderbook.on_chain.utils.ext_fract import *


from opshin.prelude import *
from opshin.ledger.interval import *


@dataclass()
class OrderParams(PlutusData):
    """
    Unchangable parameters of an order
    """

    CONSTR_ID = 0
    owner_pkh: PubKeyHash
    owner_address: Address
    buy: Token
    sell: Token
    # to be interpreted as a boolean
    allow_partial: int
    # allow returning the remaining amount after expiry
    expiry_date: ExtendedPOSIXTime
    # to be withheld by the batcher for expiry
    return_reward: int
    # amount attached to the order for minUTxO (usually 2-2.5 ADA)
    min_utxo: int


@dataclass()
class Order(PlutusData):
    CONSTR_ID = 0
    params: OrderParams
    buy_amount: int
    # Marks that the order is a continuation of another order
    continuation_of: Union[TxOutRef, Nothing]
    # to be withheld by the batcher for matching
    batch_reward: int


@dataclass()
class CancelOrder(PlutusData):
    CONSTR_ID = 1
    input_index: int


@dataclass()
class FullMatch(PlutusData):
    CONSTR_ID = 2
    input_index: int
    output_index: int


@dataclass()
class PartialMatch(PlutusData):
    CONSTR_ID = 3
    input_index: int
    output_index: int
    filled_amount: int


@dataclass()
class ReturnExpired(PlutusData):
    CONSTR_ID = 4
    input_index: int
    output_index: int


OrderAction = Union[CancelOrder, FullMatch, PartialMatch, ReturnExpired]


# This datum has to accompany the output associated with the order
OutDatum = TxOutRef

Lovelace = Token(b"", b"")

# Primary DID NFT policy accepted by the orderbook. This must match the
# permissioned DID minting policy deployed for the current testnet release.
DID_NFT_POLICY_ID = b"\xfa\x46\xb0\xa2\xf3\x93\x01\xfe\x0d\x68\x69\x35\x49\x9c\xd8\x83\x5f\x69\xfc\x98\x70\x7c\x52\x83\xd8\xfd\x60\x66"

def has_did_token_in_inputs(
    user_address: Address, policy_id: bytes, required_token_name: bytes, tx_info: TxInfo
) -> bool:
    """
    Check whether a user spends a positive DID token matching a policy and
    optional token name. Spending the DID UTxO requires the user's wallet
    signature, so this proves wallet-level DID ownership for this transaction.
    """
    empty_token_dict: Dict[TokenName, int] = {}
    for tx_input in tx_info.inputs:
        if tx_input.resolved.address == user_address:
            tokens = tx_input.resolved.value.get(policy_id, empty_token_dict)
            for token_amount in tokens.items():
                token_name = token_amount[0]
                amount = token_amount[1]
                if amount > 0 and (
                    required_token_name == b"" or required_token_name == token_name
                ):
                    return True
    return False


def has_primary_did(user_address: Address, tx_info: TxInfo) -> bool:
    return has_did_token_in_inputs(user_address, DID_NFT_POLICY_ID, b"", tx_info)


def check_owner_did(order: Order, tx_info: TxInfo) -> None:
    assert has_primary_did(order.params.owner_address, tx_info), "DID_OWNER"


def check_counterparty_did(order: Order, tx_info: TxInfo) -> None:
    owner_address = order.params.owner_address
    has_counterparty_did = False
    for input_info in tx_info.inputs:
        input_address = input_info.resolved.address
        if input_address != owner_address and has_primary_did(input_address, tx_info):
            has_counterparty_did = True
    assert has_counterparty_did, "DID_COUNTERPARTY"


def valid_range_ends_at_or_before_expiry(
    expiry: ExtendedPOSIXTime, tx_info: TxInfo
) -> bool:
    upper = tx_info.valid_range.upper_bound.limit
    if isinstance(expiry, PosInfPOSIXTime):
        return True
    if isinstance(expiry, NegInfPOSIXTime):
        return False
    if isinstance(upper, NegInfPOSIXTime):
        return True
    if isinstance(upper, PosInfPOSIXTime):
        return False
    if isinstance(expiry, FinitePOSIXTime):
        if isinstance(upper, FinitePOSIXTime):
            return upper.time <= expiry.time
    return False


def valid_range_starts_at_or_after_expiry(
    expiry: ExtendedPOSIXTime, tx_info: TxInfo
) -> bool:
    lower = tx_info.valid_range.lower_bound.limit
    if isinstance(expiry, PosInfPOSIXTime):
        return False
    if isinstance(expiry, NegInfPOSIXTime):
        return True
    if isinstance(lower, PosInfPOSIXTime):
        return True
    if isinstance(lower, NegInfPOSIXTime):
        return False
    if isinstance(expiry, FinitePOSIXTime):
        if isinstance(lower, FinitePOSIXTime):
            return lower.time >= expiry.time
    return False


def check_out_datum(output: TxOut, input_ref: TxOutRef, tx_info: TxInfo) -> None:
    """
    Check that the output datum references the input order
    TODO this leads to breaking transaction chaining which is unfortunate
    """
    out_datum: OutDatum = resolve_datum_unsafe(output, tx_info)
    assert out_datum == input_ref, "1"


def check_cancel(order: Order, tx_info: TxInfo, own_input: TxInInfo) -> None:
    """
    Check that the creator of the order has signed the transaction,
    which allows the owner to do anything with the order
    """

    # check if owner cancels
    assert (
        order.params.owner_pkh in tx_info.signatories
    ), "2"
    check_owner_did(order, tx_info)


def check_full(
    order: Order, own_input: TxInInfo, own_output: TxOut, tx_info: TxInfo
) -> None:
    # check that the output datum is set correctly
    # NOTE: No need to enforce the out ref is unique, this is true by default

    # check that we have new output datum for order
    order_params = order.params
    assert valid_range_ends_at_or_before_expiry(order_params.expiry_date, tx_info), "EXP_FILL"
    check_counterparty_did(order, tx_info)
    new_out_datum = Order(order_params, 0, own_input.out_ref, 0)

    output_datum: Order = resolve_datum_unsafe(own_output, tx_info)
    assert output_datum == new_out_datum, "3"

    # make sure that the order creator gets at least what they ordered
    # 1) check that the output actually remains at the contract - this is to ensure the DID layer where the user has to cancel
    own_input_resolved = own_input.resolved
    assert own_output.address == own_input_resolved.address, "5"

    # 2) the value is at least the buy amount
    order_params = order.params
    owned_after = own_output.value

    buy_token = order.params.buy
    expected_owned_after = add_lovelace(
        {
            buy_token.policy_id: {buy_token.token_name: order.buy_amount},
        },
        order_params.min_utxo,
    )
    check_greater_or_equal_value(
        owned_after,
        expected_owned_after,
    )


def check_partial(
    order: Order,
    filled_amount: int,
    own_input_info: TxInInfo,
    own_output: TxOut,
    tx_info: TxInfo,
):
    """
    Check that the order is partially filled and the continuing output is set correctly
    """
    check_counterparty_did(order, tx_info)

    # 1) check that the ratio is valid
    order_buy_amount = order.buy_amount
    assert 0 < filled_amount < order_buy_amount, "6"
    assert order.params.allow_partial == 1, "PARTIAL_DISABLED"
    assert valid_range_ends_at_or_before_expiry(order.params.expiry_date, tx_info), "EXP_FILL"

    # 2) check that the output datum is set correctly
    new_buy_amount = order_buy_amount - filled_amount
    order_params = order.params
    order_batch_reward = order.batch_reward
    scaled_batch_reward = floor_scale_fraction(
        filled_amount, order_buy_amount, order_batch_reward
    )
    remaining_reward = order_batch_reward - scaled_batch_reward

    new_out_datum = Order(
        order_params, new_buy_amount, own_input_info.out_ref, remaining_reward
    )
    output_datum: Order = resolve_datum_unsafe(own_output, tx_info)
    assert output_datum == new_out_datum, "3"

    # 3) check that the output actually remains at the contract
    own_input = own_input_info.resolved
    assert own_output.address == own_input.address, "5"

    # 4) check that the value is modified correctly
    own_input_value = own_input.value
    sell_token = order_params.sell
    sell_owned_before = token_amount_in_value(own_input_value, sell_token)
    if sell_token.policy_id == b"":  # i.e. sell token is lovelace
        sell_owned_before -= order_params.min_utxo
    just_bought = filled_amount
    just_sold = floor_scale_fraction(filled_amount, order_buy_amount, sell_owned_before)

    total_owned_after = own_output.value
    total_owned_before = own_input_value
    buy_token = order_params.buy
    sell_token = order_params.sell
    # need to use subtract_lovelace to account for the option that either buy or sell token is lovelace
    delta = subtract_lovelace(
        # construct value manually for cheaper computation
        # NOTE: this expects buy and sell token to be distinct, which is reasonable
        # A non-distinct case would only affect the user who placed the order
        {
            buy_token.policy_id: {buy_token.token_name: just_bought},
            sell_token.policy_id: {sell_token.token_name: -just_sold},
        },
        scaled_batch_reward,
    )
    expected_owned_after = add_value(total_owned_before, delta)
    check_greater_or_equal_value(
        total_owned_after,
        expected_owned_after,
    )


def check_return_expired(
    order: Order,
    own_input: TxInInfo,
    own_output: TxOut,
    tx_info: TxInfo,
) -> None:
    """
    Check that the remaining amount is returned to the owner after expiry
    """
    # 1) check that the output datum is set correctly
    # NOTE: No need to enforce the out ref is unique, this is true by default
    assert valid_range_starts_at_or_after_expiry(
        order.params.expiry_date, tx_info
    ), "EXP_RETURN"
    check_owner_did(order, tx_info)
    check_out_datum(own_output, own_input.out_ref, tx_info)

    # 2) check that the output actually goes to the owner
    order_params = order.params
    assert own_output.address == order_params.owner_address, "5"

    # 3) check that the value is modified correctly
    owned_before = own_input.resolved.value
    owned_after = own_output.value
    expected_owned_after = subtract_lovelace(owned_before, order_params.return_reward)
    check_greater_or_equal_value(owned_after, expected_owned_after)


# build with
# $ opshin build spending src/on_chain/orderbook/opshin_orderbook_v3.py '{"bytes": "..."}'
def validator(
    withdrawal_validator: StakingHash,
    order: Order,
    redeemer: OrderAction,
    context: ScriptContext,
) -> None:
    tx_info = context.tx_info
    purpose: Spending = context.purpose

    if isinstance(redeemer, CancelOrder):
        own_input = tx_info.inputs[redeemer.input_index]
        own_out_ref = purpose.tx_out_ref
        assert (
            own_out_ref == own_input.out_ref
        ), "B"
        check_cancel(order, tx_info, own_input)
    else:
        own_input = tx_info.inputs[redeemer.input_index]

        # Obtain the own input and address
        own_out_ref = purpose.tx_out_ref
        assert (
            own_out_ref == own_input.out_ref
        ), "B"

        own_output = tx_info.outputs[redeemer.output_index]
        # check the spender specific logic
        if isinstance(redeemer, FullMatch):
            # The creator of the order receives the full amount
            check_full(order, own_input, own_output, tx_info)
        elif isinstance(redeemer, PartialMatch):
            # The order is partially filled and the continuing output is set correctly
            check_partial(order, redeemer.filled_amount, own_input, own_output, tx_info)
        elif isinstance(redeemer, ReturnExpired):
            # Return expired order
            check_return_expired(order, own_input, own_output, tx_info)
        else:
            assert False, "C"
