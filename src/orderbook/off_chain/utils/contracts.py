import json
from pathlib import Path
from typing import Optional, Tuple

import cbor2
from pycardano import (
    PaymentVerificationKey,
    PaymentSigningKey,
    Address,
    Network,
    PlutusV2Script,
    plutus_script_hash,
    ChainContext,
    PlutusV1Script,
    UTxO,
)

from orderbook.off_chain.utils import network
from orderbook.off_chain.utils.keys import get_address

build_dir = Path(__file__).parent.parent.parent.joinpath("on_chain/build")

# File to store reference script UTxO location
REF_SCRIPT_FILE = build_dir.joinpath("reference_scripts.json")


def module_name(module):
    return Path(module.__file__).stem


def get_contract(name, compressed=False, context: ChainContext = None):
    """Get contract script, hash, and address."""
    with open(
        build_dir.joinpath(f"{name}{'_compressed' if compressed else ''}/script.cbor")
    ) as f:
        contract_cbor_hex = f.read().strip()
    contract_cbor = bytes.fromhex(contract_cbor_hex)

    contract_plutus_script = PlutusV2Script(contract_cbor)

    contract_script_hash = plutus_script_hash(contract_plutus_script)
    contract_script_address = Address(contract_script_hash, network=Network.TESTNET)

    return contract_plutus_script, contract_script_hash, contract_script_address


def get_pluto_contract(name):
    with open(build_dir.joinpath(f"{name}.plutus")) as f:
        contract_plutus = json.load(f)
    contract_cbor = cbor2.loads(bytes.fromhex(contract_plutus["cborHex"]))

    contract_plutus_script = PlutusV1Script(contract_cbor)
    contract_script_hash = plutus_script_hash(contract_plutus_script)
    contract_script_address = Address(contract_script_hash, network=network)
    return contract_plutus_script, contract_script_hash, contract_script_address


def get_ref_utxo(
    contract: PlutusV2Script,
    context: ChainContext,
    custom_script_address: Optional[Address] = None,
) -> Optional[UTxO]:
    """Find a UTxO containing the contract as a reference script at the given address."""
    if custom_script_address is None:
        return None
    
    try:
        for utxo in context.utxos(custom_script_address):
            if utxo.output.script == contract:
                return utxo
    except Exception:
        pass
    return None


def save_reference_utxo(contract_name: str, tx_id: str, index: int, address: str):
    """Save reference script UTxO location to file."""
    data = {}
    if REF_SCRIPT_FILE.exists():
        with open(REF_SCRIPT_FILE) as f:
            data = json.load(f)
    
    data[contract_name] = {
        "tx_id": tx_id,
        "index": index,
        "address": address
    }
    
    with open(REF_SCRIPT_FILE, "w") as f:
        json.dump(data, f, indent=2)


def load_reference_utxo_info(contract_name: str) -> Optional[dict]:
    """Load reference script UTxO info from file."""
    if not REF_SCRIPT_FILE.exists():
        return None
    
    with open(REF_SCRIPT_FILE) as f:
        data = json.load(f)
    
    return data.get(contract_name)


def find_reference_utxo(
    contract_name: str,
    context: ChainContext,
    search_addresses: Optional[list] = None,
) -> Optional[UTxO]:
    """Find the reference script UTxO for a contract.
    
    First checks the saved location, then searches provided addresses.
    """
    contract_script, _, _ = get_contract(contract_name, False, context)
    
    # Try saved location first
    saved_info = load_reference_utxo_info(contract_name)
    if saved_info:
        try:
            address = Address.from_primitive(saved_info["address"])
            ref_utxo = get_ref_utxo(contract_script, context, address)
            if ref_utxo is not None:
                return ref_utxo
        except Exception:
            pass
    
    # Search provided addresses
    if search_addresses:
        for address in search_addresses:
            ref_utxo = get_ref_utxo(contract_script, context, address)
            if ref_utxo is not None:
                return ref_utxo
    
    return None
