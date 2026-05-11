from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = PROJECT_ROOT / "src"
DATA_DIR = PROJECT_ROOT / "runtime" / "did_dex"
DB_PATH = DATA_DIR / "did_dex.sqlite3"
ISSUER_KEY_NAME = "did_issuer"
REGISTRATION_HASH_KEY = b"did-dex-catalyst-demo-registration-key-v1"


def _read(path: Path, fallback: str = "") -> str:
    try:
        return path.read_text().strip()
    except FileNotFoundError:
        return fallback


ORDERBOOK_BUILD_DIR = SRC_ROOT / "orderbook" / "on_chain" / "build" / "orderbook"
FREE_MINT_BUILD_DIR = SRC_ROOT / "orderbook" / "on_chain" / "build" / "free_mint"
DID_BUILD_DIR = (
    SRC_ROOT
    / "auth_nft_minting_tool"
    / "onchain"
    / "build"
    / "did_nft"
)

NETWORK = "preprod"
ORDERBOOK_SCRIPT_HASH = _read(ORDERBOOK_BUILD_DIR / "script.policy_id")
ORDERBOOK_ADDRESS = _read(ORDERBOOK_BUILD_DIR / "testnet.addr")
FREE_MINT_POLICY_ID = _read(FREE_MINT_BUILD_DIR / "script.policy_id")
DID_POLICY_ID = _read(
    DID_BUILD_DIR / "script.policy_id",
    "3280db0e2bf08e6f96463a238d4faa8c4c7d7885a65199c9dd91abd8",
)

MIN_UTXO = 2_300_000
RETURN_REWARD = 650_000
BATCH_REWARD = 650_000
DEFAULT_ORDER_TTL_MS = 24 * 60 * 60 * 1000


@dataclass(frozen=True)
class AssetConfig:
    policy_id: str
    asset_name: str
    ticker: str
    decimals: int = 0

    @property
    def unit(self) -> str:
        return f"{self.policy_id}{self.asset_name}"

    @property
    def is_lovelace(self) -> bool:
        return self.policy_id == "" and self.asset_name == ""


@dataclass(frozen=True)
class PairConfig:
    id: str
    base: AssetConfig
    quote: AssetConfig


SUPPORTED_PAIRS = [
    PairConfig(
        id="ada-muesli",
        base=AssetConfig(
            policy_id="",
            asset_name="",
            ticker="ADA",
            decimals=6,
        ),
        quote=AssetConfig(
            policy_id=FREE_MINT_POLICY_ID,
            asset_name="6d7565736c69",
            ticker="MUESLI",
        ),
    ),
    PairConfig(
        id="ada-swap",
        base=AssetConfig(
            policy_id="",
            asset_name="",
            ticker="ADA",
            decimals=6,
        ),
        quote=AssetConfig(
            policy_id=FREE_MINT_POLICY_ID,
            asset_name="73776170",
            ticker="SWAP",
        ),
    ),
    PairConfig(
        id="muesli-swap",
        base=AssetConfig(
            policy_id=FREE_MINT_POLICY_ID,
            asset_name="6d7565736c69",
            ticker="MUESLI",
        ),
        quote=AssetConfig(
            policy_id=FREE_MINT_POLICY_ID,
            asset_name="73776170",
            ticker="SWAP",
        ),
    )
]


def get_pair(pair_id: str) -> PairConfig:
    for pair in SUPPORTED_PAIRS:
        if pair.id == pair_id:
            return pair
    raise KeyError(f"Unsupported pair: {pair_id}")


def public_config() -> dict:
    return {
        "network": NETWORK,
        "didPolicyId": DID_POLICY_ID,
        "orderbookScriptHash": ORDERBOOK_SCRIPT_HASH,
        "orderbookAddress": ORDERBOOK_ADDRESS,
        "fees": {
            "minUtxo": MIN_UTXO,
            "returnReward": RETURN_REWARD,
            "batchReward": BATCH_REWARD,
        },
        "pairs": [
            {
                "id": pair.id,
                "base": pair.base.__dict__,
                "quote": pair.quote.__dict__,
            }
            for pair in SUPPORTED_PAIRS
        ],
    }
