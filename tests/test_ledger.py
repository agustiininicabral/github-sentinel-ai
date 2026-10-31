import sqlite3

from sentinel_api.ledger import DeliveryLedger


def test_delivery_is_processed_once_and_acknowledged(tmp_path):
    ledger = DeliveryLedger(str(tmp_path / "sentinel.db"))
    payload = {"action": "opened", "pull_request": {"title": "test"}}
    assert ledger.register("delivery-1", "pull_request", "opened", payload)
    assert not ledger.register("delivery-1", "pull_request", "opened", payload)
    pending = ledger.pending()
    assert len(pending) == 1
    assert pending[0]["payload"] == payload
    assert ledger.acknowledge("delivery-1")
    assert not ledger.acknowledge("delivery-1")
    assert ledger.pending() == []


def test_ledger_migrates_previous_delivery_table(tmp_path):
    database = tmp_path / "legacy.db"
    with sqlite3.connect(database) as connection:
        connection.execute("""
            CREATE TABLE deliveries (
                delivery_id TEXT PRIMARY KEY,
                event_name TEXT NOT NULL,
                action TEXT,
                received_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)
        connection.execute(
            "INSERT INTO deliveries(delivery_id, event_name, action) VALUES (?, ?, ?)",
            ("legacy-1", "pull_request", "opened"),
        )
    ledger = DeliveryLedger(str(database))
    pending = ledger.pending()
    assert len(pending) == 1
    assert pending[0]["delivery_id"] == "legacy-1"
    assert pending[0]["payload"] == {}


def test_in_memory_ledger_survives_per_operation_connections():
    ledger = DeliveryLedger(":memory:")
    try:
        payload = {"action": "opened"}
        assert ledger.register("memory-1", "pull_request", "opened", payload)
        assert ledger.pending()[0]["payload"] == payload
        assert ledger.ping()
        assert ledger.acknowledge("memory-1")
        assert ledger.pending() == []
    finally:
        ledger.close()


def test_pending_limit_is_clamped(tmp_path):
    ledger = DeliveryLedger(str(tmp_path / "limits.db"))
    for index in range(3):
        assert ledger.register(f"delivery-{index}", "ping", None, {})
    assert len(ledger.pending(0)) == 1
    assert len(ledger.pending(500)) == 3
