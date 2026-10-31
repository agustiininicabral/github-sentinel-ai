import hashlib
import hmac
import json

import httpx
import pytest

from sentinel_api import main


def signed(body: bytes, secret: str) -> str:
    return "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


async def request_app():
    async with main.app.router.lifespan_context(main.app):
        transport = httpx.ASGITransport(app=main.app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            yield client


@pytest.mark.asyncio
async def test_health_and_ready(monkeypatch, tmp_path):
    monkeypatch.setattr(main.settings, "database_path", str(tmp_path / "api.db"))
    async for client in request_app():
        assert (await client.get("/health")).status_code == 200
        assert (await client.get("/ready")).json()["status"] == "ready"


@pytest.mark.asyncio
async def test_webhook_signature_risk_deduplication_and_outbox(monkeypatch, tmp_path):
    monkeypatch.setattr(main.settings, "github_webhook_secret", "test-secret")
    monkeypatch.setattr(main.settings, "integration_token", "n8n-secret")
    monkeypatch.setattr(main.settings, "database_path", str(tmp_path / "api.db"))
    body = json.dumps({"action": "opened", "pull_request": {
        "title": "Auth update", "labels": [], "changed_files": 25
    }}).encode()
    headers = {"X-GitHub-Event": "pull_request", "X-GitHub-Delivery": "delivery-42",
               "X-Hub-Signature-256": signed(body, "test-secret")}
    async for client in request_app():
        first = await client.post("/webhooks/github", content=body, headers=headers)
        second = await client.post("/webhooks/github", content=body, headers=headers)
        unauthorized = await client.get("/integrations/n8n/events")
        pending = await client.get("/integrations/n8n/events", headers={"Authorization": "Bearer n8n-secret"})
        ack = await client.post("/integrations/n8n/events/delivery-42/ack",
                                headers={"Authorization": "Bearer n8n-secret"})
        empty = await client.get("/integrations/n8n/events", headers={"Authorization": "Bearer n8n-secret"})
        ack_again = await client.post("/integrations/n8n/events/delivery-42/ack",
                                      headers={"Authorization": "Bearer n8n-secret"})
    assert first.status_code == 200
    assert first.json()["risk"]["level"] == "medium"
    assert first.json()["risk"]["score"] == 45
    assert second.json()["status"] == "duplicate"
    assert unauthorized.status_code == 401
    assert pending.json()["count"] == 1
    assert pending.json()["events"][0]["payload"]["action"] == "opened"
    assert ack.json()["status"] == "processed"
    assert empty.json()["count"] == 0
    assert ack_again.status_code == 404


@pytest.mark.asyncio
async def test_webhook_rejects_invalid_signature(monkeypatch, tmp_path):
    monkeypatch.setattr(main.settings, "github_webhook_secret", "test-secret")
    monkeypatch.setattr(main.settings, "database_path", str(tmp_path / "api.db"))
    async for client in request_app():
        response = await client.post("/webhooks/github", content=b"{}", headers={
            "X-GitHub-Event": "ping", "X-GitHub-Delivery": "delivery-bad",
            "X-Hub-Signature-256": "sha256=" + "0" * 64})
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_webhook_rejects_oversized_payload(monkeypatch, tmp_path):
    monkeypatch.setattr(main.settings, "database_path", str(tmp_path / "large.db"))
    monkeypatch.setattr(main.settings, "max_webhook_bytes", 1024)
    async for client in request_app():
        response = await client.post("/webhooks/github", content=b"x" * 1025)
    assert response.status_code == 413


@pytest.mark.asyncio
async def test_webhook_rejects_non_object_json(monkeypatch, tmp_path):
    monkeypatch.setattr(main.settings, "github_webhook_secret", "test-secret")
    monkeypatch.setattr(main.settings, "database_path", str(tmp_path / "shape.db"))
    body = b"[]"
    async for client in request_app():
        response = await client.post("/webhooks/github", content=body, headers={
            "X-GitHub-Event": "ping", "X-GitHub-Delivery": "delivery-array",
            "X-Hub-Signature-256": signed(body, "test-secret")})
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_n8n_integration_is_disabled_without_token(monkeypatch, tmp_path):
    monkeypatch.setattr(main.settings, "integration_token", "")
    monkeypatch.setattr(main.settings, "database_path", str(tmp_path / "disabled.db"))
    async for client in request_app():
        response = await client.get("/integrations/n8n/events")
    assert response.status_code == 503


@pytest.mark.asyncio
async def test_ai_advisory_runs_on_authenticated_n8n_endpoint(monkeypatch, tmp_path):
    monkeypatch.setattr(main.settings, "github_webhook_secret", "test-secret")
    monkeypatch.setattr(main.settings, "integration_token", "n8n-secret")
    monkeypatch.setattr(main.settings, "ai_enabled", True)
    monkeypatch.setattr(main.settings, "database_path", str(tmp_path / "ai.db"))

    async def fake_summary(settings, assessment, title):
        assert assessment["score"] == 25
        assert title == "Auth update"
        return "Review the authentication change carefully."

    monkeypatch.setattr(main, "summarize_risk", fake_summary)
    body = json.dumps({"action": "opened", "pull_request": {"title": "Auth update"}}).encode()
    headers = {"X-GitHub-Event": "pull_request", "X-GitHub-Delivery": "ai-delivery",
               "X-Hub-Signature-256": signed(body, "test-secret")}
    async for client in request_app():
        webhook = await client.post("/webhooks/github", content=body, headers=headers)
        unauthorized = await client.post("/integrations/n8n/analyze", json={
            "delivery_id": "ai-delivery", "payload": json.loads(body)
        })
        analysis = await client.post("/integrations/n8n/analyze", json={
            "delivery_id": "ai-delivery", "payload": json.loads(body)
        }, headers={"Authorization": "Bearer n8n-secret"})
    assert webhook.status_code == 200
    assert "ai_summary" not in webhook.json()
    assert unauthorized.status_code == 401
    assert analysis.json()["risk"]["score"] == 25
    assert analysis.json()["ai_summary"] == "Review the authentication change carefully."


@pytest.mark.asyncio
async def test_ai_provider_failure_does_not_block_webhook_or_analysis(monkeypatch, tmp_path):
    monkeypatch.setattr(main.settings, "github_webhook_secret", "test-secret")
    monkeypatch.setattr(main.settings, "integration_token", "n8n-secret")
    monkeypatch.setattr(main.settings, "ai_enabled", True)
    monkeypatch.setattr(main.settings, "database_path", str(tmp_path / "ai-failure.db"))

    async def failing_summary(settings, assessment, title):
        raise RuntimeError("local model is unavailable")

    monkeypatch.setattr(main, "summarize_risk", failing_summary)
    body = json.dumps({"action": "opened", "pull_request": {"title": "Auth update"}}).encode()
    headers = {"X-GitHub-Event": "pull_request", "X-GitHub-Delivery": "ai-failure",
               "X-Hub-Signature-256": signed(body, "test-secret")}
    async for client in request_app():
        webhook = await client.post("/webhooks/github", content=body, headers=headers)
        analysis = await client.post("/integrations/n8n/analyze", json={
            "delivery_id": "ai-failure", "payload": json.loads(body)
        }, headers={"Authorization": "Bearer n8n-secret"})
    assert webhook.status_code == 200
    assert analysis.status_code == 200
    assert analysis.json()["ai_summary_status"] == "unavailable"


@pytest.mark.asyncio
async def test_analyze_requires_delivery_and_payload(monkeypatch):
    monkeypatch.setattr(main.settings, "integration_token", "n8n-secret")
    async for client in request_app():
        missing_id = await client.post("/integrations/n8n/analyze", json={"payload": {}},
                                       headers={"Authorization": "Bearer n8n-secret"})
        invalid_payload = await client.post("/integrations/n8n/analyze", json={
            "delivery_id": "delivery-1", "payload": []
        }, headers={"Authorization": "Bearer n8n-secret"})
    assert missing_id.status_code == 400
    assert invalid_payload.status_code == 400
