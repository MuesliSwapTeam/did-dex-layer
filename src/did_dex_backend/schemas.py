from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field


class DIDRegisterRequest(BaseModel):
    walletAddress: str
    displayName: str
    country: str
    idType: Literal["PASSPORT", "NATIONAL_ID", "DRIVERS_LICENSE"]
    idNumber: str


class DIDMintTxRequest(BaseModel):
    registrationId: int


class DIDCheckRequest(BaseModel):
    walletAddress: str


class DIDConfirmRequest(BaseModel):
    registrationId: int
    txHash: str


class TokenCheckRequest(BaseModel):
    walletAddress: str
    pairId: str = "muesli-swap"


class TokenMintTxRequest(BaseModel):
    walletAddress: str
    pairId: str = "muesli-swap"
    baseAmount: int = Field(default=1_000_000, gt=0, le=10_000_000)
    quoteAmount: int = Field(default=1_000_000, gt=0, le=10_000_000)


class PlaceOrderRequest(BaseModel):
    walletAddress: str
    pairId: str = "muesli-swap"
    side: Literal["sell_base", "sell_quote"]
    sellAmount: int = Field(gt=0)
    buyAmount: int = Field(gt=0)
    allowPartial: bool = True


class CancelOrderRequest(BaseModel):
    walletAddress: str
    orderRef: str
    pairId: str = "muesli-swap"


class FillOrderRequest(BaseModel):
    walletAddress: str
    orderRef: str
    pairId: str = "muesli-swap"
    fillAmount: Optional[int] = Field(default=None, gt=0)


class TradeFillEvent(BaseModel):
    type: Literal["fill"]
    pairId: str
    orderRef: str
    makerAddress: str
    takerAddress: str
    side: Literal["sell_base", "sell_quote"]
    price: float = Field(gt=0)
    amount: int = Field(gt=0)
    quoteAmount: int = Field(gt=0)


class TxConfirmRequest(BaseModel):
    walletAddress: str
    txHash: str
    event: TradeFillEvent
