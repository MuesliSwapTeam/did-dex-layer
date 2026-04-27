from __future__ import annotations

import hashlib
import hmac
import re
from dataclasses import dataclass

from .config import REGISTRATION_HASH_KEY


ID_RE = re.compile(r"^[A-Z0-9][A-Z0-9 -]{2,62}[A-Z0-9]$")
NAME_RE = re.compile(r"^[A-Za-z][A-Za-z .'-]{1,78}[A-Za-z]$")


@dataclass(frozen=True)
class NormalizedRegistration:
    display_name: str
    country: str
    id_type: str
    id_number: str

    @property
    def stable_value(self) -> str:
        return f"{self.country}|{self.id_type}|{self.id_number}"


def normalize_registration(
    display_name: str, country: str, id_type: str, id_number: str
) -> NormalizedRegistration:
    normalized = NormalizedRegistration(
        display_name=" ".join(display_name.strip().split()),
        country=country.strip().upper(),
        id_type=id_type.strip().upper().replace(" ", "_"),
        id_number=" ".join(id_number.strip().upper().split()),
    )

    if not NAME_RE.match(normalized.display_name):
        raise ValueError("Name must contain 3-80 letters/spaces and simple punctuation.")
    if len(normalized.country) != 2 or not normalized.country.isalpha():
        raise ValueError("Country must be a two-letter ISO country code.")
    if normalized.id_type not in {"PASSPORT", "NATIONAL_ID", "DRIVERS_LICENSE"}:
        raise ValueError("Unsupported ID type.")
    if not ID_RE.match(normalized.id_number):
        raise ValueError("ID number has an unsupported format.")
    return normalized


def registration_hash(normalized: NormalizedRegistration) -> str:
    return hmac.new(
        REGISTRATION_HASH_KEY,
        normalized.stable_value.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def did_asset_name(id_hash: str, wallet_address: str) -> str:
    digest = hashlib.sha256(f"{id_hash}|{wallet_address}".encode("utf-8")).digest()
    return digest[:32].hex()

