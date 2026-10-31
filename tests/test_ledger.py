from sentinel_api.ledger import DeliveryLedger


def test_delivery_is_processed_once(tmp_path):
    ledger = DeliveryLedger(str(tmp_path / "sentinel.db"))
    assert ledger.register("delivery-1", "pull_request", "opened")
    assert not ledger.register("delivery-1", "pull_request", "opened")
