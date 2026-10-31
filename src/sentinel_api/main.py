import json
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Header, HTTPException, Request

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


app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)


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

    raw_body = await request.body()
    if len(raw_body) > settings.max_webhook_bytes:
        raise HTTPException(status_code=413, detail="Webhook payload too large")
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
    is_new = request.app.state.ledger.register(x_github_delivery, x_github_event, action)
    if not is_new:
        return {"status": "duplicate", "delivery_id": x_github_delivery}

    result = {"status": "accepted", "delivery_id": x_github_delivery, "event": x_github_event, "action": action}
    if x_github_event == "pull_request" and isinstance(payload.get("pull_request"), dict):
        result["risk"] = assess_pull_request(payload).to_dict()
    logger.info("github_delivery_received event=%s action=%s delivery=%s", x_github_event, action, x_github_delivery)
    return result
