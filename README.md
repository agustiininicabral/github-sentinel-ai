# GitHub Sentinel AI

Enterprise-oriented, local-first GitHub DevOps, QA and code-intelligence automation. Sentinel receives GitHub webhooks, verifies their HMAC signature, deduplicates deliveries, computes deterministic pull-request risk signals, and exposes an auditable API for downstream automation such as n8n.

> Current scope: secure webhook intake and risk triage. AI review, PostgreSQL, richer GitHub actions and n8n orchestration are roadmap items—not claimed as implemented.

## Features
- FastAPI service with health and readiness endpoints.
- GitHub webhook signature verification against the exact raw request body.
- Bounded streaming request-body handling and delivery-id idempotency ledger (SQLite by default).
- Deterministic PR risk scoring with explainable factors, using GitHub's actual nested webhook schema.
- Optional OpenAI-compatible AI advisory adapter; local-compatible endpoints are supported and deterministic mode works without AI credentials.
- Environment-based configuration, structured logs and automated tests.
- GitHub Actions CI for Python 3.12 with coverage reporting.

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
See [.env.example](.env.example). Set a high-entropy `GITHUB_WEBHOOK_SECRET` before accepting webhooks. `MAX_WEBHOOK_BYTES` defaults to 1 MiB. Keep secrets outside Git. `AI_ENABLED=false` is the safe default. To use a local OpenAI-compatible server, set `AI_BASE_URL` and `AI_MODEL`; the adapter is opt-in and advisory only.

## GitHub webhook
Configure a repository webhook with:
- Payload URL: your reachable HTTPS URL + `/webhooks/github`
- Content type: `application/json`
- Secret: same value as `GITHUB_WEBHOOK_SECRET`
- Events: Pull requests (start with this only)

The endpoint verifies `X-Hub-Signature-256` over the original raw bytes and uses `X-GitHub-Delivery` to prevent duplicate processing. Do not expose the service without HTTPS, secret management, rate limiting and an operational deployment plan.

## Tests
```powershell
pytest --cov=sentinel_api --cov-report=term-missing
ruff check src tests
```

## Architecture
```text
GitHub webhook -> bounded FastAPI ingress -> HMAC verification -> idempotency ledger
                                                               -> PR risk engine
                                                               -> JSON acknowledgement
                                                               -> optional AI advisory adapter
```

## Security boundaries
- No automatic merges, pushes, approvals, or destructive GitHub writes.
- AI output is advisory and must never be treated as authorization.
- Webhook signature is checked before JSON parsing or persistence.
- SQLite is suitable for local development/single-instance use; use PostgreSQL before multi-instance production.
- n8n must not parse and re-serialize the signed GitHub body before signature verification.
- Never commit `.env`, tokens, webhook secrets, or model credentials.

## Roadmap
1. PostgreSQL repository and migrations.
2. n8n workflows with a verified raw-body ingress and human approval gates.
3. GitHub App authentication with least-privilege permissions.
4. PR diff analysis, test selection, security findings and quality trends.
5. AI-assisted review with strict data minimization and deterministic fallbacks.

## License
MIT.
