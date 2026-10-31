# GitHub Sentinel AI

Enterprise-oriented, local-first GitHub DevOps, QA and code-intelligence automation. Sentinel receives GitHub webhooks, verifies their HMAC signature, deduplicates deliveries, computes deterministic pull-request risk signals, and exposes an authenticated durable outbox for n8n.

> Implemented milestone: secure webhook intake, SQLite outbox, n8n polling/acknowledgement workflow and an optional OpenAI-compatible AI adapter. PostgreSQL, automated PR diff review and GitHub write actions remain future work.

## Features
- FastAPI service with health and readiness endpoints.
- GitHub webhook signature verification against the exact raw request body.
- Bounded streaming request-body handling and delivery-id idempotency ledger.
- Durable SQLite outbox for verified webhook deliveries, with forward schema migration.
- Authenticated n8n polling and acknowledgement endpoints.
- Importable n8n workflow for scheduled polling and event normalization.
- Deterministic PR risk scoring with explainable factors, using GitHub's actual nested webhook schema.
- Optional OpenAI-compatible AI advisory adapter; local-compatible endpoints are supported and deterministic mode works without AI credentials.
- GitHub Actions CI with Ruff linting and pytest coverage gate (85%).

## Quick start (Windows PowerShell)
```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -e ".[dev]"
Copy-Item .env.example .env
python -m sentinel_api
```
Open http://127.0.0.1:8000/docs and http://127.0.0.1:8000/health.

## Configuration
See [.env.example](.env.example). Set a high-entropy `GITHUB_WEBHOOK_SECRET` and a different high-entropy `SENTINEL_INTEGRATION_TOKEN`. `MAX_WEBHOOK_BYTES` defaults to 1 MiB. Keep secrets outside Git. `AI_ENABLED=false` is the safe default. To use a local OpenAI-compatible server, set `AI_BASE_URL` and `AI_MODEL`; the adapter is opt-in and advisory only.

## GitHub webhook
Configure a repository webhook with:
- Payload URL: your reachable HTTPS URL + `/webhooks/github`
- Content type: `application/json`
- Secret: same value as `GITHUB_WEBHOOK_SECRET`
- Events: Pull requests (start with this only)

The endpoint verifies `X-Hub-Signature-256` over the original raw bytes and persists verified events to the outbox. Do not expose the service without HTTPS, secret management, rate limiting and an operational deployment plan.

## n8n
Import [n8n/github-sentinel-secure-intake.json](n8n/github-sentinel-secure-intake.json) and follow [docs/N8N_INTEGRATION.md](docs/N8N_INTEGRATION.md). n8n uses a separate bearer token to poll pending events and acknowledge each delivery. The workflow export contains a credential placeholder; configure the HTTP Header Auth credential after import.

## Tests
```powershell
pytest --cov=sentinel_api --cov-report=term-missing
ruff check src tests
```

## Architecture
```text
GitHub webhook -> bounded FastAPI ingress -> HMAC verification -> SQLite outbox
                                                                -> n8n polling API
                                                                -> PR risk engine
                                                                -> optional AI advisory adapter
```

## Security boundaries
- No automatic merges, pushes, approvals, or destructive GitHub writes.
- AI output is advisory and must never be treated as authorization.
- Webhook signature is checked before JSON parsing or persistence.
- SQLite is intended for local/single-instance use; use PostgreSQL before multi-instance production.
- n8n receives only events already verified by Sentinel. Never parse and re-serialize the signed GitHub body before verification.
- Never commit `.env`, tokens, webhook secrets, or model credentials.

## Roadmap
1. PostgreSQL repository and migrations.
2. GitHub App authentication with least-privilege permissions.
3. PR diff analysis, test selection, security findings and quality trends.
4. AI-assisted review with strict data minimization, deterministic fallbacks and human approval gates.

## License
MIT.
