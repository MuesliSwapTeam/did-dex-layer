from pathlib import Path

from pycardano import PaymentVerificationKey, PaymentSigningKey, Address, Network

from orderbook.off_chain.utils.network import network

keys_dir = Path(__file__).parent.parent.parent.parent.joinpath("keys")


def get_address(name) -> Address:
    with open(
        keys_dir.joinpath(f"{name}.{'test_' if network == Network.TESTNET else ''}addr")
    ) as f:
        address = Address.from_primitive(f.read())
    return address


def get_signing_info(name, network=network):
    skey_path = str(keys_dir.joinpath(f"{name}.skey"))
    payment_skey = PaymentSigningKey.load(skey_path)
    payment_vkey = PaymentVerificationKey.from_signing_key(payment_skey)
    payment_address = Address(payment_vkey.hash(), network=network)
    return payment_vkey, payment_skey, payment_address