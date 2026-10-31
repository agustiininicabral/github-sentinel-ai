import httpx

from .config import Settings


async def summarize_risk(settings: Settings, assessment: dict, pr_title: str) -> str | None:
    """Optional OpenAI-compatible advisory call; never authorizes a GitHub action."""
    if not settings.ai_enabled or not settings.ai_base_url or not settings.ai_model:
        return None
    endpoint = settings.ai_base_url.rstrip("/") + "/chat/completions"
    headers = {"Authorization": f"Bearer {settings.ai_api_key}"} if settings.ai_api_key else {}
    payload = {
        "model": settings.ai_model,
        "temperature": 0,
        "messages": [
            {"role": "system", "content": "Summarize this deterministic PR risk assessment. Do not invent facts or authorize actions."},
            {"role": "user", "content": f"PR: {pr_title}\nAssessment: {assessment}"},
        ],
    }
    async with httpx.AsyncClient(timeout=settings.ai_timeout_seconds) as client:
        response = await client.post(endpoint, headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()
    return data["choices"][0]["message"]["content"]
