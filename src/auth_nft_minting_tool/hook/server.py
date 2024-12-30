from __future__ import annotations
from typing import Annotated, List, Any, Literal, Optional
from pydantic import BaseModel

from fastapi import FastAPI, HTTPException
from fastapi.responses import RedirectResponse, ORJSONResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi_cache import FastAPICache, Coder
from fastapi_cache.decorator import cache
from fastapi_cache.backends.inmemory import InMemoryBackend
import uvicorn
from flask import Response
import logging

import pycardano
from pycardano import Transaction
from nacl.hash import blake2b
from nacl.encoding import RawEncoder
from cbor2 import dumps, loads
import peewee as pw
import random
from datetime import datetime
import hashlib


DID_NFT_POLICY_ID = "358587601623527cb63a89afba9873a97c407df960d19e21e11f6d15"
DB_FILE_NAME = "../users.db"
CHALLENGE_VALIDITY = 300  # seconds

db = pw.SqliteDatabase(DB_FILE_NAME)


class User(pw.Model):
    connect_did = pw.CharField(unique=True, null=False)
    atala_did = pw.CharField(null=True)
    challenge = pw.CharField(null=True)
    challenge_timestamp = pw.DateTimeField(null=True)

    class Meta:
        database = db


# logger setup
_LOGGER = logging.getLogger()
logging.basicConfig(
    format="%(asctime)s %(levelname)-8s %(message)s", level=logging.DEBUG
)

app = FastAPI(
    default_response_class=ORJSONResponse,
    title="Webhook for Proofspace",
    description="A webhook needed for our DID Proofspace Demo",
    version="0.0.1",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # List of origins that are allowed to make requests
    allow_credentials=True,  # Whether to support credentials (cookies, Authorization headers)
    allow_methods=["*"],  # Allow all methods or specify ["GET", "POST", etc.]
    allow_headers=[
        "*"
    ],  # Allow all headers or specify ["X-Custom-Header", "Content-Type", etc.]
)


# Define the Pydantic models
class ActionParam(BaseModel):
    name: str
    value: str


class WebhookCredentialField(BaseModel):
    name: str
    value: str


class WebhookCredentialValuesDTO(BaseModel):
    credentialId: str
    schemaId: str
    fields: List[WebhookCredentialField]


class InteractionWebhookRequest(BaseModel):
    publicServiceDid: str
    subscriberConnectDid: str
    actionId: str
    actionInstanceId: str
    actionEventId: str
    actionParams: List[ActionParam]
    receivedCredentials: List[WebhookCredentialValuesDTO]


class InteractionWebhookResponse(BaseModel):
    serviceDid: str
    subscriberConnectDid: str
    actionEventId: str
    issuedCredentials: List[WebhookCredentialValuesDTO]


@app.post("/interaction-webhook")
async def interaction_webhook(
    webhook_data: InteractionWebhookRequest,
) -> InteractionWebhookResponse:
    db.connect()
    db.create_tables([User])
    db.execute_sql("PRAGMA journal_mode=WAL;")
    User.replace(
        connect_did=webhook_data.subscriberConnectDid,
        atala_did=webhook_data.receivedCredentials[0].fields[0].value,
        challenge=str(random.randint(2**20, 2**30)),
        challenge_timestamp=datetime.now(),
    ).execute()
    db.commit()
    db.close()

    return InteractionWebhookResponse(
        serviceDid=webhook_data.publicServiceDid,
        subscriberConnectDid=webhook_data.subscriberConnectDid,
        actionEventId=webhook_data.actionEventId,
        issuedCredentials=[],
    )


def get_signing_info(name, network=pycardano.Network.MAINNET):
    skey_path = f"keys/{name}.skey"
    payment_skey = pycardano.PaymentSigningKey.load(skey_path)
    payment_vkey = pycardano.PaymentVerificationKey.from_signing_key(payment_skey)
    payment_address = pycardano.Address(payment_vkey.hash(), network=network)
    return payment_vkey, payment_skey, payment_address


@app.get("/signature")
async def signature_endpoint(tx_cbor: str):
    x = loads(bytes.fromhex(tx_cbor))

    minted = pycardano.MultiAsset.from_primitive(x[0][9])
    did_pid = pycardano.ScriptHash.from_primitive(bytes.fromhex(DID_NFT_POLICY_ID))
    did_names = [i for i in minted[did_pid].items()]
    success = True
    if len(did_names) != 1 or did_names[0][1] != 1:
        success = False
    minted_did = str(did_names[0][0])

    atala_did = x[3][2001]
    challenge_response = x[3][2002]

    # get this user's challenge from DB
    db.connect()
    user = User.select().where(User.atala_did == "did:prism:" + atala_did).get()
    db.close()

    if (datetime.now() - user.challenge_timestamp).total_seconds() > CHALLENGE_VALIDITY:
        success = False
    if hashlib.sha256(user.challenge.encode()).hexdigest() != challenge_response:
        success = False

    desired_tokenname = hashlib.sha256(atala_did.encode()).hexdigest()[:32]
    if bytes.fromhex(minted_did).decode("utf-8") != desired_tokenname:
        success = False

    if not success:
        return JSONResponse(
            {
                "signature": None,
                "status": "error",
            }
        )

    vk, sk, _ = get_signing_info("signer")
    tx_hash = blake2b(dumps(x[0]), 32, encoder=RawEncoder)
    signature = sk.sign(tx_hash)
    vk_witness = pycardano.VerificationKeyWitness(vkey=vk, signature=signature)
    return JSONResponse(
        {
            "signature": vk_witness.to_cbor_hex(),
            "status": "success",
        }
    )


if __name__ == "__main__":
    db.connect()
    db.create_tables([User])
    db.execute_sql("PRAGMA journal_mode=WAL;")
    db.close()
    uvicorn.run(app, host="localhost", port=6000)
