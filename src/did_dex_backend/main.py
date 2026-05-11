from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from . import chain, config, database, tx_builders
from .schemas import (
    CancelOrderRequest,
    DIDCheckRequest,
    DIDConfirmRequest,
    DIDMintTxRequest,
    DIDRegisterRequest,
    FillOrderRequest,
    PlaceOrderRequest,
    TokenCheckRequest,
    TokenMintTxRequest,
    TxConfirmRequest,
)
from .security import did_asset_name, normalize_registration, registration_hash


app = FastAPI(title="DID DEX Backend", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup() -> None:
    database.init_db()


@app.get("/api/config")
def get_config() -> dict:
    return config.public_config()


@app.post("/api/did/register")
def register_did(request: DIDRegisterRequest) -> dict:
    try:
        normalized = normalize_registration(
            request.displayName, request.country, request.idType, request.idNumber
        )
        id_hash = registration_hash(normalized)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    asset_name = did_asset_name(id_hash, request.walletAddress)
    registration = database.create_registration(request.walletAddress, id_hash, asset_name)
    return {"registration": registration}


@app.post("/api/did/check")
def check_did(request: DIDCheckRequest) -> dict:
    registration = database.get_wallet_registration(request.walletAddress)
    status = chain.did_status(request.walletAddress, registration)
    if status["hasDid"] and registration and registration["status"] != "minted":
        registration = database.mark_minted(registration["id"])
        status["registration"] = registration
    return status


def require_wallet_did(wallet_address: str) -> None:
    status = chain.did_status(wallet_address, database.get_wallet_registration(wallet_address))
    if not status.get("chainAvailable", True):
        raise HTTPException(
            status_code=503,
            detail=status.get("error") or "Cardano chain context is not available",
        )
    if status.get("addressValid") is False:
        raise HTTPException(
            status_code=400,
            detail=status.get("error") or chain.PREPROD_ADDRESS_ERROR,
        )
    if not status["hasDid"]:
        raise HTTPException(status_code=403, detail="Wallet does not hold a valid DID NFT")


def tx_error(exc: Exception) -> HTTPException:
    detail = str(exc)
    if chain.LEGACY_CONTRACT_MARKER in detail.lower():
        detail = "DID minting contract dependencies are not available."
    if isinstance(exc, chain.ChainUnavailable):
        return HTTPException(status_code=503, detail=detail)
    if isinstance(exc, KeyError):
        return HTTPException(status_code=400, detail=detail)
    if isinstance(exc, ValueError):
        if "Order UTxO not found" in detail:
            return HTTPException(status_code=404, detail=detail)
        if "Wallet does not hold the required DID NFT" in detail:
            return HTTPException(status_code=403, detail=detail)
        return HTTPException(status_code=400, detail=detail)
    return HTTPException(status_code=503, detail=detail)


@app.post("/api/did/mint-tx")
def did_mint_tx(request: DIDMintTxRequest) -> dict:
    registration = database.get_registration(request.registrationId)
    if registration is None:
        raise HTTPException(status_code=404, detail="Registration not found")
    if registration["status"] not in {"approved", "submitted"}:
        raise HTTPException(status_code=409, detail="Registration is not mintable")
    try:
        return tx_builders.build_did_mint_tx(registration)
    except Exception as exc:
        raise tx_error(exc) from exc


@app.post("/api/did/confirm")
def did_confirm(request: DIDConfirmRequest) -> dict:
    registration = database.mark_submitted(request.registrationId, request.txHash)
    if registration is None:
        raise HTTPException(status_code=404, detail="Registration not found")
    return {"registration": registration}


@app.post("/api/tokens/check")
def check_tokens(request: TokenCheckRequest) -> dict:
    try:
        return chain.token_balances(request.walletAddress, request.pairId)
    except Exception as exc:
        raise tx_error(exc) from exc


@app.post("/api/tokens/mint-tx")
def token_mint_tx(request: TokenMintTxRequest) -> dict:
    try:
        return tx_builders.build_test_token_mint_tx(request)
    except Exception as exc:
        raise tx_error(exc) from exc


@app.get("/api/orders")
def get_orders(pairId: str = "muesli-swap") -> dict:
    try:
        return {"orders": chain.list_orders(pairId)}
    except Exception as exc:
        raise tx_error(exc) from exc


@app.get("/api/analytics")
def get_analytics(pairId: str = "muesli-swap") -> dict:
    try:
        return chain.analytics(pairId)
    except Exception as exc:
        raise tx_error(exc) from exc


@app.get("/api/trades")
def get_trades(pairId: str = "muesli-swap", limit: int = 50) -> dict:
    try:
        return {"trades": chain.list_trades(pairId, limit)}
    except Exception as exc:
        raise tx_error(exc) from exc


@app.post("/api/tx/place-order")
def place_order(request: PlaceOrderRequest) -> dict:
    require_wallet_did(request.walletAddress)
    try:
        return tx_builders.build_place_order_tx(request)
    except Exception as exc:
        raise tx_error(exc) from exc


@app.post("/api/tx/cancel-order")
def cancel_order(request: CancelOrderRequest) -> dict:
    require_wallet_did(request.walletAddress)
    try:
        return tx_builders.build_cancel_order_tx(request)
    except Exception as exc:
        raise tx_error(exc) from exc


@app.post("/api/tx/fill-order")
def fill_order(request: FillOrderRequest) -> dict:
    require_wallet_did(request.walletAddress)
    try:
        return tx_builders.build_fill_order_tx(request)
    except Exception as exc:
        raise tx_error(exc) from exc


@app.post("/api/tx/confirm")
def confirm_tx(request: TxConfirmRequest) -> dict:
    require_wallet_did(request.walletAddress)
    event = request.event
    if event.takerAddress != request.walletAddress:
        raise HTTPException(status_code=400, detail="Wallet does not match trade event taker")
    trade = database.record_trade_fill(
        pair_id=event.pairId,
        tx_hash=request.txHash,
        order_ref=event.orderRef,
        maker_address=event.makerAddress,
        taker_address=event.takerAddress,
        side=event.side,
        price=event.price,
        amount=event.amount,
        quote_amount=event.quoteAmount,
        created_at=chain.transaction_time(request.txHash),
    )
    return {"trade": chain._trade_row_to_api(trade)}


frontend_dist = Path(__file__).resolve().parents[1] / "did_dex_frontend" / "dist"
if frontend_dist.exists():
    app.mount("/", StaticFiles(directory=frontend_dist, html=True), name="frontend")
