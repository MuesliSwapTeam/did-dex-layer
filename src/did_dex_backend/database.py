from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from typing import Optional

from .config import DB_PATH, DID_POLICY_ID


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with connect() as conn:
        conn.execute(
            """
            create table if not exists did_registration (
                id integer primary key autoincrement,
                wallet_address text not null,
                id_hash text not null unique,
                asset_name text not null,
                policy_id text not null,
                status text not null,
                tx_hash text,
                created_at text not null,
                minted_at text
            )
            """
        )
        conn.execute(
            "create index if not exists idx_did_wallet on did_registration(wallet_address)"
        )
        conn.execute(
            """
            create table if not exists dex_trade_fill (
                id integer primary key autoincrement,
                pair_id text not null,
                tx_hash text not null unique,
                order_ref text not null,
                maker_address text not null,
                taker_address text not null,
                side text not null,
                price real not null,
                amount integer not null,
                quote_amount integer not null,
                created_at text not null
            )
            """
        )
        conn.execute(
            "create index if not exists idx_trade_fill_pair_time on dex_trade_fill(pair_id, created_at desc)"
        )


def row_to_dict(row: sqlite3.Row | None) -> Optional[dict]:
    return dict(row) if row is not None else None


def create_registration(wallet_address: str, id_hash: str, asset_name: str) -> dict:
    init_db()
    now = utcnow()
    with connect() as conn:
        existing = conn.execute(
            "select * from did_registration where id_hash = ?", (id_hash,)
        ).fetchone()
        if existing is not None:
            return dict(existing)
        conn.execute(
            """
            insert into did_registration
            (wallet_address, id_hash, asset_name, policy_id, status, created_at)
            values (?, ?, ?, ?, 'approved', ?)
            """,
            (wallet_address, id_hash, asset_name, DID_POLICY_ID, now),
        )
        row = conn.execute(
            "select * from did_registration where id_hash = ?", (id_hash,)
        ).fetchone()
        return dict(row)


def get_registration(registration_id: int) -> Optional[dict]:
    init_db()
    with connect() as conn:
        return row_to_dict(
            conn.execute(
                "select * from did_registration where id = ?", (registration_id,)
            ).fetchone()
        )


def get_wallet_registration(wallet_address: str) -> Optional[dict]:
    init_db()
    with connect() as conn:
        return row_to_dict(
            conn.execute(
                """
                select * from did_registration
                where wallet_address = ?
                order by id desc
                limit 1
                """,
                (wallet_address,),
            ).fetchone()
        )


def mark_submitted(registration_id: int, tx_hash: str) -> Optional[dict]:
    init_db()
    with connect() as conn:
        conn.execute(
            """
            update did_registration
            set tx_hash = ?, status = 'submitted'
            where id = ?
            """,
            (tx_hash, registration_id),
        )
        return row_to_dict(
            conn.execute(
                "select * from did_registration where id = ?", (registration_id,)
            ).fetchone()
        )


def mark_minted(registration_id: int, tx_hash: str | None = None) -> Optional[dict]:
    init_db()
    with connect() as conn:
        current_tx_hash = tx_hash
        if current_tx_hash is None:
            row = conn.execute(
                "select tx_hash from did_registration where id = ?", (registration_id,)
            ).fetchone()
            current_tx_hash = row["tx_hash"] if row is not None else None
        conn.execute(
            """
            update did_registration
            set tx_hash = coalesce(?, tx_hash), status = 'minted', minted_at = ?
            where id = ?
            """,
            (current_tx_hash, utcnow(), registration_id),
        )
        return row_to_dict(
            conn.execute(
                "select * from did_registration where id = ?", (registration_id,)
            ).fetchone()
        )


def record_trade_fill(
    *,
    pair_id: str,
    tx_hash: str,
    order_ref: str,
    maker_address: str,
    taker_address: str,
    side: str,
    price: float,
    amount: int,
    quote_amount: int,
    created_at: str | None = None,
) -> dict:
    init_db()
    timestamp = created_at or utcnow()
    with connect() as conn:
        conn.execute(
            """
            insert into dex_trade_fill
            (pair_id, tx_hash, order_ref, maker_address, taker_address, side, price, amount, quote_amount, created_at)
            values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            on conflict(tx_hash) do update set
                pair_id = excluded.pair_id,
                order_ref = excluded.order_ref,
                maker_address = excluded.maker_address,
                taker_address = excluded.taker_address,
                side = excluded.side,
                price = excluded.price,
                amount = excluded.amount,
                quote_amount = excluded.quote_amount,
                created_at = excluded.created_at
            """,
            (
                pair_id,
                tx_hash,
                order_ref,
                maker_address,
                taker_address,
                side,
                price,
                amount,
                quote_amount,
                timestamp,
            ),
        )
        return dict(
            conn.execute(
                "select * from dex_trade_fill where tx_hash = ?", (tx_hash,)
            ).fetchone()
        )


def list_trade_fills(pair_id: str, limit: int = 50) -> list[dict]:
    init_db()
    safe_limit = max(1, min(limit, 200))
    with connect() as conn:
        return [
            dict(row)
            for row in conn.execute(
                """
                select * from dex_trade_fill
                where pair_id = ?
                order by created_at desc, id desc
                limit ?
                """,
                (pair_id, safe_limit),
            ).fetchall()
        ]
