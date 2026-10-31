import hashlib
import hmac
import json

from fastapi.testclient import TestClient

from sentinel_api import main


def signed(body: bytes, secret: str) -> str:
    return "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


def test_health_and_ready(monkeypatch, tmp_path):
    monkeypatch.setattr(main.settings, "database_path", str(tmp_path / "api.db"))
    with TestClient(main.app) as client:
        assert client.get("/health").status_code == 200
        assert client.get("/ready").json()["status"] == "ready"


def test_webhook_signature_risk_and_deduplication(monkeypatch, tmp_path):
    monkeypatch.setattr(main.settings, "github_webhook_secret", "test-secret")
    monkeypatch.setattr(main.settings, "database_path", str(tmp_path / "api.db"))
    body = json.dumps({"action": "opened", "pull_request": {"title": "Auth update", "labels": []},
                       "changed_files": 2}).encode()
    headers = {"X-GitHub-Event": "pull_request", "X-GitHub-Delivery": "delivery-42",
               "X-Hub-Signature-256": signed(body, "test-secret")}
    with TestClient(main.app) as client:
        first = client.post("/webhooks/github", content=body, headers=headers)
        second = client.post("/webhooks/github", content=body, headers=headers)
    assert first.status_code == 200
    assert first.json()["risk"]["level"] == "low"
    assert second.json()["status"] == "duplicate"


def test_webhook_rejects_invalid_signature(monkeypatch, tmp_path):
    monkeypatch.setattr(main.settings, "github_webhook_secret", "test-secret")
    monkeypatch.setattr(main.settings, "database_path", str(tmp_path / "api.db"))
    with TestClient(main.app) as client:
        response = client.post("/webhooks/github", content=b"{}", headers={
            "X-GitHub-Event": "ping", "X-GitHub-Delivery": "delivery-bad",
            "X-Hub-Signature-256": "sha256=" + "0" * 64})
    assert response.status_code == 401
