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
