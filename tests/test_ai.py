import httpx
import pytest

from sentinel_api import ai
from sentinel_api.config import Settings


@pytest.mark.asyncio
async def test_ai_disabled_returns_none():
    settings = Settings(ai_enabled=False)
    assert await ai.summarize_risk(settings, {"score": 0}, "Docs") is None


@pytest.mark.asyncio
async def test_ai_adapter_uses_configured_compatible_endpoint(monkeypatch):
    settings = Settings(ai_enabled=True, ai_base_url="http://local-model/v1/",
                        ai_api_key="local-key", ai_model="qwen-local")
    observed = {}

    def handler(request: httpx.Request) -> httpx.Response:
        observed["url"] = str(request.url)
        observed["authorization"] = request.headers.get("authorization")
        observed["payload"] = request.read().decode()
        return httpx.Response(200, json={"choices": [{"message": {"content": "Review summary"}}]})

    original_client = httpx.AsyncClient

    def client_factory(*, timeout):
        return original_client(transport=httpx.MockTransport(handler), timeout=timeout)

    monkeypatch.setattr(ai.httpx, "AsyncClient", client_factory)
    result = await ai.summarize_risk(settings, {"score": 25}, "Auth change")
    assert result == "Review summary"
    assert observed["url"] == "http://local-model/v1/chat/completions"
    assert observed["authorization"] == "Bearer local-key"
    assert "qwen-local" in observed["payload"]
