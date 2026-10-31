import hmac
import json
import logging
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, Header, HTTPException, Query, Request

from .ai import summarize_risk
from .config import get_settings
from .ledger import DeliveryLedger
from .risk import assess_pull_request
from .security import verify_github_signature

settings = get_settings()
logging.basicConfig(level=getattr(logging, settings.log_level.upper(), logging.INFO))
logger = logging.getLogger("sentinel")


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.ledger = DeliveryLedger(settings.database_path)
    yield


app = FastAPI(title=settings.app_name, version="0.2.0", lifespan=lifespan)


def require_integration_token(authorization: str) -> None:
    if not settings.integration_token:
        raise HTTPException(status_code=503, detail="n8n integration is not configured")
    expected = f"Bearer {settings.integration_token}"
    if not hmac.compare_digest(authorization, expected):
        raise HTTPException(status_code=401, detail="Invalid integration credentials")


@app.get("/health")
async def health():
    return {"status": "ok", "service": settings.app_name}


@app.get("/ready")
async def ready(request: Request):
    if not hasattr(request.app.state, "ledger"):
        raise HTTPException(status_code=503, detail="Ledger is not initialized")
    return {"status": "ready"}


@app.post("/webhooks/github")
async def github_webhook(
    request: Request,
    x_github_event: str = Header(default="", alias="X-GitHub-Event"),
    x_github_delivery: str = Header(default="", alias="X-GitHub-Delivery"),
    x_hub_signature_256: str = Header(default="", alias="X-Hub-Signature-256"),
):
    content_length = request.headers.get("content-length")
    if content_length:
        try:
            if int(content_length) > settings.max_webhook_bytes:
                raise HTTPException(status_code=413, detail="Webhook payload too large")
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid Content-Length header") from None

    body = bytearray()
    async for chunk in request.stream():
        if len(body) + len(chunk) > settings.max_webhook_bytes:
            raise HTTPException(status_code=413, detail="Webhook payload too large")
        body.extend(chunk)
    raw_body = bytes(body)

    if not verify_github_signature(settings.github_webhook_secret, raw_body, x_hub_signature_256):
        raise HTTPException(status_code=401, detail="Invalid webhook signature")
    if not x_github_delivery or not x_github_event:
        raise HTTPException(status_code=400, detail="Missing GitHub delivery or event header")
    try:
        payload = json.loads(raw_body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        raise HTTPException(status_code=400, detail="Invalid JSON payload") from None
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="Webhook payload must be a JSON object")

    action = payload.get("action")
    is_new = request.app.state.ledger.register(x_github_delivery, x_github_event, action, payload)
    if not is_new:
        return {"status": "duplicate", "delivery_id": x_github_delivery}

    result = {"status": "accepted", "delivery_id": x_github_delivery, "event": x_github_event, "action": action}
    if x_github_event == "pull_request" and isinstance(payload.get("pull_request"), dict):
        assessment = assess_pull_request(payload).to_dict()
        result["risk"] = assessment
        if settings.ai_enabled:
            try:
                summary = await summarize_risk(
                    settings, assessment, str(payload["pull_request"].get("title") or "")
                )
                if summary:
                    result["ai_summary"] = summary
            except (httpx.HTTPError, KeyError, IndexError, TypeError, ValueError):
                logger.exception("ai_advisory_failed delivery=%s", x_github_delivery)
                result["ai_summary_status"] = "unavailable"
    logger.info("github_delivery_enqueued event=%s action=%s delivery=%s", x_github_event, action, x_github_delivery)
    return result


@app.get("/integrations/n8n/events")
async def n8n_pending_events(
    request: Request,
    limit: int = Query(default=20, ge=1, le=100),
    authorization: str = Header(default="", alias="Authorization"),
):
    require_integration_token(authorization)
    events = request.app.state.ledger.pending(limit)
    return {"events": events, "count": len(events)}


@app.post("/integrations/n8n/events/{delivery_id}/ack")
async def n8n_acknowledge_event(
    delivery_id: str,
    request: Request,
    authorization: str = Header(default="", alias="Authorization"),
):
    require_integration_token(authorization)
    if not request.app.state.ledger.acknowledge(delivery_id):
        raise HTTPException(status_code=404, detail="Pending delivery not found")
    return {"status": "processed", "delivery_id": delivery_id}
