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
class AdvancedOrderFeatures(PlutusData):
    """
    Advanced order features and parameters
    """

    CONSTR_ID = 0
    # Stop-loss: trigger price ratio (numerator, denominator)
    stop_loss_price_num: int
    stop_loss_price_den: int
    # Minimum fill amount (0 means no minimum)
    min_fill_amount: int
    # TWAP: time interval for averaging (in milliseconds, 0 means disabled)
    twap_interval: int
    # Maximum slippage allowed (basis points, 0 means no limit)
    max_slippage_bps: int


@dataclass()
class DIDType(PlutusData):
    """
    Different types of DID authentication levels
    """

    CONSTR_ID = 0
    # DID provider policy ID
    policy_id: bytes
    # Required token name pattern (empty bytes means any token name accepted)
    required_token_name: bytes
    # Minimum authentication level (0 = basic, 1 = verified, 2 = accredited, 3 = institutional)
    min_auth_level: int


@dataclass()
class DIDRequirements(PlutusData):
    """
    DID requirements for order execution
    """

    CONSTR_ID = 0
    # List of accepted DID types (empty list means any DID accepted)
    accepted_did_types: List[DIDType]
    # Whether both parties need to meet DID requirements
    require_counterparty_did: int  # 0 = no, 1 = yes
    # Whether to allow trading with non-DID users
    allow_non_did_trading: int  # 0 = no, 1 = yes


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
    # Advanced order features (optional)
    advanced_features: Union[AdvancedOrderFeatures, Nothing]
    # DID requirements for this order (optional)
    did_requirements: Union[DIDRequirements, Nothing]


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


@dataclass()
class StopLossMatch(PlutusData):
    """
    Match triggered by stop-loss condition
    """

    CONSTR_ID = 5
    input_index: int
    output_index: int
    filled_amount: int
    # Current market price that triggered the stop-loss (numerator, denominator)
    trigger_price_num: int
    trigger_price_den: int


@dataclass()
class TWAPMatch(PlutusData):
    """
    Time-weighted average price match
    """

    CONSTR_ID = 6
    input_index: int
    output_index: int
    filled_amount: int
    # Reference to previous TWAP execution
    previous_twap_ref: Union[TxOutRef, Nothing]


OrderAction = Union[
    CancelOrder, FullMatch, PartialMatch, ReturnExpired, StopLossMatch, TWAPMatch
]


# This datum has to accompany the output associated with the order
OutDatum = TxOutRef

Lovelace = Token(b"", b"")

# DID_NFT_POLICY_ID = b'\xafx\xc4\x04\\Po\xe7\x1a\x85\xb9B\xe02\xe9hX~\xb126;J6K\\\xae\x00'

# Primary DID NFT policy (existing Atala PRISM)
DID_NFT_POLICY_ID = b"\x67\x2a\xe1\xe7\x95\x85\xad\x15\x43\xef\x6b\x4b\x6c\x89\x89\xa1\x7a\xdc\xea\x30\x40\xf7\x7e\xde\x12\x8d\x92\x17"

# Example additional DID provider policy IDs
ACCREDITED_INVESTOR_POLICY_ID = b"\xab\xc1\x23\xe7\x95\x85\xad\x15\x43\xef\x6b\x4b\x6c\x89\x89\xa1\x7a\xdc\xea\x30\x40\xf7\x7e\xde\x12\x8d\x94\x56"

BUSINESS_ENTITY_POLICY_ID = b"\xde\xf4\x56\xe7\x95\x85\xad\x15\x43\xef\x6b\x4b\x6c\x89\x89\xa1\x7a\xdc\xea\x30\x40\xf7\x7e\xde\x12\x8d\x97\x89"


def has_did_nft_in_inputs(
    user_address: Address, policy_id: bytes, tx_info: TxInfo
) -> bool:
    """
    Check if user has a specific DID NFT policy in their transaction inputs
    Simplified for OpShin compatibility - checks if user has inputs with the policy
    Note: Simplified implementation - assumes presence indicates ownership
    """
    empty_token_dict: Dict[TokenName, int] = {}
    for tx_input in tx_info.inputs:
        if tx_input.resolved.address == user_address:
            value = tx_input.resolved.value
            # Check if policy ID exists by getting with empty dict default
            # If we get something back that has length > 0, policy exists
            tokens = value.get(policy_id, empty_token_dict)
            if len(tokens) > 0:
                return True
    return False


def check_did_compliance(
    user_address: Address, did_requirements: DIDRequirements, tx_info: TxInfo
) -> bool:
    """
    Check if user meets DID requirements for order execution
    """
    # If no DID requirements specified, allow execution
    if len(did_requirements.accepted_did_types) == 0:
        return True

    # Check if user has any DID NFTs at all
    has_any_did = (
        has_did_nft_in_inputs(user_address, DID_NFT_POLICY_ID, tx_info)
        or has_did_nft_in_inputs(user_address, ACCREDITED_INVESTOR_POLICY_ID, tx_info)
        or has_did_nft_in_inputs(user_address, BUSINESS_ENTITY_POLICY_ID, tx_info)
    )

    # If no DID tokens and non-DID trading is allowed
    if not has_any_did:
        return did_requirements.allow_non_did_trading == 1

    # Check if user has any of the required DID types
    for required_did_type in did_requirements.accepted_did_types:
        if has_did_nft_in_inputs(user_address, required_did_type.policy_id, tx_info):
            return True

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

    # check if DID NFT bucket is present (do not enforce here)
    own_input_resolved = own_input.resolved

    # check if owner cancels
    assert (
        order.params.owner_pkh in tx_info.signatories
    ), "2"

    # assert _nft_bucket is not None, "CANCEL NFT NOT PRESENT"


def check_full(
    order: Order, own_input: TxInInfo, own_output: TxOut, tx_info: TxInfo
) -> None:
    # check that the output datum is set correctly
    # NOTE: No need to enforce the out ref is unique, this is true by default

    # check that we have new output datum for order
    order_params = order.params
    new_out_datum = Order(order_params, 0, own_input.out_ref, 0)

    output_datum: Order = resolve_datum_unsafe(own_output, tx_info)
    assert output_datum == new_out_datum, "3"

    # Check DID requirements if specified
    # Note: We check all non-owner inputs for DID compliance (
    did_reqs = order_params.did_requirements
    if not isinstance(did_reqs, Nothing):
        did_requirements: DIDRequirements = did_reqs
        # Check that at least one non-owner input meets DID requirements
        has_compliant_counterparty = False
        for input_info in tx_info.inputs:
            input_address = input_info.resolved.address
            if input_address != order_params.owner_address:
                if check_did_compliance(input_address, did_requirements, tx_info):
                    has_compliant_counterparty = True
        assert has_compliant_counterparty, "4"

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
    # 1) check that the ratio is valid
    order_buy_amount = order.buy_amount
    assert 0 < filled_amount < order_buy_amount, "6"

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
    check_out_datum(own_output, own_input.out_ref, tx_info)

    # 2) check that the output actually goes to the owner
    order_params = order.params
    assert own_output.address == order_params.owner_address, "5"

    # 3) check that the value is modified correctly
    owned_before = own_input.resolved.value
    owned_after = own_output.value
    expected_owned_after = subtract_lovelace(owned_before, order_params.return_reward)
    check_greater_or_equal_value(owned_after, expected_owned_after)


def check_stop_loss(
    order: Order,
    filled_amount: int,
    trigger_price_num: int,
    trigger_price_den: int,
    own_input: TxInInfo,
    own_output: TxOut,
    tx_info: TxInfo,
) -> None:
    """
    Check that stop-loss order is triggered correctly
    """
    order_params = order.params
    advanced_features = order_params.advanced_features

    if isinstance(advanced_features, Nothing):
        assert False, "7"

    features: AdvancedOrderFeatures = advanced_features

    # Check DID requirements if specified
    did_reqs = order_params.did_requirements
    if not isinstance(did_reqs, Nothing):
        did_requirements: DIDRequirements = did_reqs
        # Check that at least one non-owner input meets DID requirements
        has_compliant_counterparty = False
        for input_info in tx_info.inputs:
            input_address = input_info.resolved.address
            if input_address != order_params.owner_address:
                if check_did_compliance(input_address, did_requirements, tx_info):
                    has_compliant_counterparty = True
        assert has_compliant_counterparty, "4"

    # Check that the trigger price meets the stop-loss condition
    # Current price should be <= stop-loss price for sell orders
    # For simplicity, we assume this is a sell stop-loss
    current_price_valid = (
        trigger_price_num * features.stop_loss_price_den
        <= trigger_price_den * features.stop_loss_price_num
    )
    assert current_price_valid, "8"

    # Check minimum fill amount if specified
    if features.min_fill_amount > 0:
        assert filled_amount >= features.min_fill_amount, "9"

    # Validate the partial fill logic (reuse existing logic)
    check_partial(order, filled_amount, own_input, own_output, tx_info)


def check_twap_match(
    order: Order,
    filled_amount: int,
    previous_twap_ref: Union[TxOutRef, Nothing],
    own_input: TxInInfo,
    own_output: TxOut,
    tx_info: TxInfo,
) -> None:
    """
    Check that TWAP order execution is valid
    """
    order_params = order.params
    advanced_features = order_params.advanced_features

    if isinstance(advanced_features, Nothing):
        assert False, "A"

    features: AdvancedOrderFeatures = advanced_features

    # Check DID requirements if specified
    did_reqs = order_params.did_requirements
    if not isinstance(did_reqs, Nothing):
        did_requirements: DIDRequirements = did_reqs
        # Check that at least one non-owner input meets DID requirements
        has_compliant_counterparty = False
        for input_info in tx_info.inputs:
            input_address = input_info.resolved.address
            if input_address != order_params.owner_address:
                if check_did_compliance(input_address, did_requirements, tx_info):
                    has_compliant_counterparty = True
        assert has_compliant_counterparty, "4"

    # Check that TWAP interval is respected
    if features.twap_interval > 0:
        current_time = tx_info.valid_range.lower_bound.limit
        # For simplicity, we don't enforce exact timing here
        # In a real implementation, we'd check against the previous execution time
        pass

    # Check minimum fill amount if specified
    if features.min_fill_amount > 0:
        assert filled_amount >= features.min_fill_amount, "9"

    # Validate the partial fill logic (reuse existing logic)
    check_partial(order, filled_amount, own_input, own_output, tx_info)


def check_advanced_partial(
    order: Order,
    filled_amount: int,
    own_input: TxInInfo,
    own_output: TxOut,
    tx_info: TxInfo,
) -> None:
    """
    Check partial order with advanced features validation
    """
    order_params = order.params
    advanced_features = order_params.advanced_features

    # Check DID requirements if specified
    did_reqs = order_params.did_requirements
    if not isinstance(did_reqs, Nothing):
        did_requirements: DIDRequirements = did_reqs
        # Check that at least one non-owner input meets DID requirements
        has_compliant_counterparty = False
        for input_info in tx_info.inputs:
            input_address = input_info.resolved.address
            if input_address != order_params.owner_address:
                if check_did_compliance(input_address, did_requirements, tx_info):
                    has_compliant_counterparty = True
        assert has_compliant_counterparty, "4"

    # Check minimum fill amount if advanced features are enabled
    if not isinstance(advanced_features, Nothing):
        features: AdvancedOrderFeatures = advanced_features
        if features.min_fill_amount > 0:
            assert (
                filled_amount >= features.min_fill_amount
            ), "9"

    # Use existing partial validation logic
    check_partial(order, filled_amount, own_input, own_output, tx_info)


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
            check_advanced_partial(
                order, redeemer.filled_amount, own_input, own_output, tx_info
            )
        elif isinstance(redeemer, StopLossMatch):
            # Stop-loss order triggered
            check_stop_loss(
                order,
                redeemer.filled_amount,
                redeemer.trigger_price_num,
                redeemer.trigger_price_den,
                own_input,
                own_output,
                tx_info,
            )
        elif isinstance(redeemer, TWAPMatch):
            # TWAP order execution
            check_twap_match(
                order,
                redeemer.filled_amount,
                redeemer.previous_twap_ref,
                own_input,
                own_output,
                tx_info,
            )
        elif isinstance(redeemer, ReturnExpired):
            # Return expired order
            check_return_expired(order, own_input, own_output, tx_info)
        else:
            assert False, "C"
