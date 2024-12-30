"""
Orderbook with DID Layer

Features:
- Allow orders to be partially filled
- Allow orders to be cancelled
- Allow orders to be automatically returned after expiry
- Allow multiple matches by the same owner in a single transaction
- Lower fees (Plutus V2 + OpShin)
- Enforces DID Authentication NFT
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

#DID_NFT_POLICY_ID = b'\xafx\xc4\x04\\Po\xe7\x1a\x85\xb9B\xe02\xe9hX~\xb126;J6K\\\xae\x00'

DID_NFT_POLICY_ID = bytes.fromhex(
    "672ae1e79585ad1543ef6b4b6c8989a17adcea3040f77ede128d9217"
)


def check_out_datum(output: TxOut, input_ref: TxOutRef, tx_info: TxInfo) -> None:
    """
    Check that the output datum references the input order
    TODO this leads to breaking transaction chaining which is unfortunate
    """
    out_datum: OutDatum = resolve_datum_unsafe(output, tx_info)
    assert out_datum == input_ref, "Invalid txout referenced in output datum"


def check_cancel(order: Order, tx_info: TxInfo, own_input: TxInInfo) -> None:
    """
    Check that the creator of the order has signed the transaction,
    which allows the owner to do anything with the order
    """

    # check if DID NFT is present
    own_input_resolved = own_input.resolved
    nft_present = own_input_resolved.value[DID_NFT_POLICY_ID].keys()[0]

    # check if owner cancels
    assert (
        order.params.owner_pkh in tx_info.signatories
    ), "Order creator signature missing"

    assert nft_present, "CANCEL NFT NOT PRESENT"


def check_full(
    order: Order, own_input: TxInInfo, own_output: TxOut, tx_info: TxInfo
) -> None:
    # check that the output datum is set correctly
    # NOTE: No need to enforce the out ref is unique, this is true by default
    
    # check that we have new output datum for order
    order_params = order.params
    new_out_datum = Order(
        order_params, 0, own_input.out_ref, 0
    )

    output_datum: Order = resolve_datum_unsafe(own_output, tx_info)
    assert output_datum == new_out_datum, "Invalid output datum"

    # make sure that the order creator gets at least what they ordered
    # 1) check that the output actually remains at the contract - this is to ensure the DID layer where the user has to cancel
    own_input_resolved = own_input.resolved
    assert own_output.address == own_input_resolved.address, "Invalid output address"

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
    assert 0 < filled_amount < order_buy_amount, "Invalid filled amount"

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
    assert output_datum == new_out_datum, "Invalid output datum"

    # 3) check that the output actually remains at the contract
    own_input = own_input_info.resolved
    assert own_output.address == own_input.address, "Invalid output address"

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
    assert own_output.address == order_params.owner_address, "Invalid output address"

    # 3) check that the value is modified correctly
    owned_before = own_input.resolved.value
    owned_after = own_output.value
    expected_owned_after = subtract_lovelace(owned_before, order_params.return_reward)
    check_greater_or_equal_value(owned_after, expected_owned_after)


def withdrawal_present(tx_info: TxInfo, own_staking_hash: StakingHash) -> bool:
    """
    Check if the withdrawal specified is present in the transaction
    """
    withdrawals = tx_info.wdrl
    for skh, _ in withdrawals.items():
        if skh == own_staking_hash:
            return True
    return False


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
        ), "Input and output references do not match"

        own_output = tx_info.outputs[redeemer.output_index]
        # check the spender specific logic
        if isinstance(redeemer, FullMatch):
            # The creator of the order receives the full amount
            check_full(order, own_input, own_output, tx_info)
        elif isinstance(redeemer, PartialMatch):
            # The order is partially filled and the continuing output is set correctly
            check_partial(order, redeemer.filled_amount, own_input, own_output, tx_info)
        else:
            assert False, "Wrong redeemer"
