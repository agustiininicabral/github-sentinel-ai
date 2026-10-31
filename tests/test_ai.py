import pytest

from sentinel_api.ai import summarize_risk
from sentinel_api.config import Settings


@pytest.mark.asyncio
async def test_ai_disabled_returns_none():
    settings = Settings(ai_enabled=False)
    assert await summarize_risk(settings, {"score": 0}, "Docs") is None
