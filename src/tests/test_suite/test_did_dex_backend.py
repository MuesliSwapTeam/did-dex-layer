from did_dex_backend import chain, database
from did_dex_backend.main import tx_error
from did_dex_backend.security import (
    did_asset_name,
    normalize_registration,
    registration_hash,
)


def test_registration_hash_is_stable_and_does_not_store_raw_id(tmp_path, monkeypatch):
    monkeypatch.setattr(database, "DB_PATH", tmp_path / "did_dex.sqlite3")
    normalized = normalize_registration(
        "Ada Lovelace", "gb", "PASSPORT", " ab 123456 "
    )
    id_hash = registration_hash(normalized)
    asset_name = did_asset_name(id_hash, "addr_test1example")

    row = database.create_registration("addr_test1example", id_hash, asset_name)

    assert row["id_hash"] == id_hash
    assert row["asset_name"] == asset_name
    assert row["status"] == "approved"
    raw_db = (tmp_path / "did_dex.sqlite3").read_bytes()
    assert b"AB 123456" not in raw_db
    assert b"Ada Lovelace" not in raw_db


def test_duplicate_registration_reuses_existing_record(tmp_path, monkeypatch):
    monkeypatch.setattr(database, "DB_PATH", tmp_path / "did_dex.sqlite3")
    normalized = normalize_registration(
        "Grace Hopper", "us", "NATIONAL_ID", "GH-123456"
    )
    id_hash = registration_hash(normalized)
    first = database.create_registration(
        "addr_test1first", id_hash, did_asset_name(id_hash, "addr_test1first")
    )
    second = database.create_registration(
        "addr_test1second", id_hash, did_asset_name(id_hash, "addr_test1second")
    )

    assert first["id"] == second["id"]
    assert second["wallet_address"] == "addr_test1first"


def test_invalid_registration_rejected():
    try:
        normalize_registration("A", "Denmark", "PASSPORT", "???")
    except ValueError as exc:
        assert "Name" in str(exc)
    else:
        raise AssertionError("Invalid registration unexpectedly passed")


def test_did_status_rejects_non_preprod_payment_address():
    status = chain.did_status(
        "addr1qy6nhz7zng2kq0ctw04vg3jn6x7egnvjursde40trpgkfgk6ytznygr2wknzsauwawhk8qn0nkflh6d54356078ye4uqdtp080"
    )

    assert status["hasDid"] is False
    assert status["addressValid"] is False
    assert status["chainAvailable"] is True
    assert "Preprod" in status["error"]


def test_trade_fill_history_is_persisted(tmp_path, monkeypatch):
    monkeypatch.setattr(database, "DB_PATH", tmp_path / "did_dex.sqlite3")

    trade = database.record_trade_fill(
        pair_id="muesli-swap",
        tx_hash="abc123",
        order_ref="order#0",
        maker_address="addr_test1maker",
        taker_address="addr_test1taker",
        side="sell_base",
        price=0.333333,
        amount=300,
        quote_amount=100,
        created_at="2026-04-24T14:26:00+00:00",
    )
    rows = database.list_trade_fills("muesli-swap")

    assert trade["tx_hash"] == "abc123"
    assert rows[0]["amount"] == 300
    assert rows[0]["quote_amount"] == 100


def test_order_ref_validation_and_error_mapping():
    assert chain.parse_ref(
        "0c4beff397d6d0c34b56b9536b5602ee2b5e9bb53ba53156673d7cb797c9e149#0"
    ) == (
        "0c4beff397d6d0c34b56b9536b5602ee2b5e9bb53ba53156673d7cb797c9e149",
        0,
    )

    try:
        chain.parse_ref("bad")
    except ValueError as exc:
        assert "Invalid order reference" in str(exc)
    else:
        raise AssertionError("Invalid order reference unexpectedly parsed")

    assert tx_error(ValueError("Order UTxO not found")).status_code == 404
    assert tx_error(ValueError("Cannot fill your own order; cancel it instead.")).status_code == 400
