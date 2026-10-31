import hashlib
import hmac
import json

import httpx
import pytest

from sentinel_api import main


def signed(body: bytes, secret: str) -> str:
    return "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


@pytest.fixture
def anyio_backend():
    return "asyncio"


async def request_app():
    """Yield an AsyncClient with the FastAPI lifespan initialized."""
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
async def test_webhook_signature_risk_and_deduplication(monkeypatch, tmp_path):
    monkeypatch.setattr(main.settings, "github_webhook_secret", "test-secret")
    monkeypatch.setattr(main.settings, "database_path", str(tmp_path / "api.db"))
    body = json.dumps({"action": "opened", "pull_request": {
        "title": "Auth update", "labels": [], "changed_files": 25
    }}).encode()
    headers = {"X-GitHub-Event": "pull_request", "X-GitHub-Delivery": "delivery-42",
               "X-Hub-Signature-256": signed(body, "test-secret")}
    async for client in request_app():
        first = await client.post("/webhooks/github", content=body, headers=headers)
        second = await client.post("/webhooks/github", content=body, headers=headers)
    assert first.status_code == 200
    assert first.json()["risk"]["level"] == "medium"
    assert first.json()["risk"]["score"] == 45
    assert second.json()["status"] == "duplicate"


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
