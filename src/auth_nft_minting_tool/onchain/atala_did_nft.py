from opshin.prelude import *

def validator(d, r, ctx: ScriptContext):
    #assert (
    #    bytes.fromhex("2ec86e38df0ec36f44da9d8fcb8c6abd15189049382b079ff0c314b9")
    #    in ctx.tx_info.signatories
    #), "Signer did not sign transaction"
    purpose = ctx.purpose
    assert isinstance(purpose, Minting), "Invalid purpose"