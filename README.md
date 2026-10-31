# GitHub Sentinel AI

Enterprise-oriented, local-first GitHub DevOps, QA and code-intelligence automation. Sentinel receives GitHub webhooks, verifies their HMAC signature, deduplicates deliveries, computes deterministic pull-request risk signals, and exposes an auditable API for downstream automation such as n8n.

> Current scope: secure webhook intake and risk triage. AI review, PostgreSQL, richer GitHub actions and n8n orchestration are roadmap items—not claimed as implemented.

## Features
- FastAPI service with health and readiness endpoints.
- GitHub webhook signature verification against the exact raw request body.
- Delivery-id idempotency ledger (SQLite by default).
- Deterministic PR risk scoring with explainable factors.
- Optional OpenAI-compatible chat endpoint for advisory summaries; deterministic mode works without AI credentials.
- Structured logs, environment-based configuration, and automated tests.
- GitHub Actions CI for Python 3.12.

## Quick start (Windows PowerShell)
```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -e ".[dev]"
Copy-Item .env.example .env
uvicorn sentinel_api.main:app --reload
```
Open http://127.0.0.1:8000/docs and http://127.0.0.1:8000/health.

## Configuration
See [.env.example](.env.example). Set a long random `GITHUB_WEBHOOK_SECRET` before exposing the webhook. Keep secrets outside Git. `AI_ENABLED=false` is the safe default.

## GitHub webhook
Configure a repository webhook with:
- Payload URL: your reachable HTTPS URL + `/webhooks/github`
- Content type: `application/json`
- Secret: same value as `GITHUB_WEBHOOK_SECRET`
- Events: Pull requests (start with this only)

The endpoint verifies `X-Hub-Signature-256` over the original raw bytes and uses `X-GitHub-Delivery` to prevent duplicate processing. Do not expose the service without HTTPS, secret management, rate limiting and an operational deployment plan.

## Tests
```powershell
pytest
```

## Architecture
```text
GitHub webhook -> FastAPI /webhooks/github -> HMAC verification -> idempotency ledger
                                                              -> PR risk engine
                                                              -> JSON response / future n8n workflows
                                                              -> optional AI advisory adapter
```

## Security boundaries
- No automatic merges, pushes, approvals, or destructive GitHub writes.
- AI output is advisory and must never be treated as authorization.
- Webhook signature is checked before JSON parsing or persistence.
- SQLite is suitable for local development/single-instance use; use PostgreSQL before multi-instance production.
- Never commit `.env`, tokens, webhook secrets, or model credentials.

## Roadmap
1. PostgreSQL repository and migrations.
2. n8n workflows with raw-body-preserving ingress and human approval gates.
3. GitHub App authentication with least-privilege permissions.
4. PR diff analysis, test selection, security findings and quality trends.
5. AI-assisted review with strict data minimization and deterministic fallbacks.

## License
MIT.
