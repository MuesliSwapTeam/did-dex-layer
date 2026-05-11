from opshin.prelude import *


EMPTY_TOKEN_DICT: Dict[TokenName, int] = {}


@dataclass()
class MintDID(PlutusData):
    CONSTR_ID = 0
    recipient_pkh: PubKeyHash
    asset_name: bytes


def validator(issuer_pkh: PubKeyHash, redeemer: MintDID, ctx: ScriptContext) -> None:
    """
    Permissioned DID NFT minting policy.

    The backend compiles/deploys this policy with the issuer public key hash as
    the script parameter. A valid mint needs the issuer signature and the
    recipient wallet signature, and can mint exactly one NFT under this policy.
    """
    purpose = ctx.purpose
    assert isinstance(purpose, Minting), "PURPOSE"

    tx_info = ctx.tx_info
    assert issuer_pkh in tx_info.signatories, "ISSUER"
    assert redeemer.recipient_pkh in tx_info.signatories, "RECIPIENT"

    own_policy = purpose.policy_id
    minted = tx_info.mint.get(own_policy, EMPTY_TOKEN_DICT)
    assert len(minted) == 1, "ONE_ASSET"
    assert minted.get(redeemer.asset_name, 0) == 1, "ONE_NFT"
