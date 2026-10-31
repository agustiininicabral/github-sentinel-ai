# Architecture

## Runtime flow
1. GitHub sends an event to `POST /webhooks/github`.
2. FastAPI streams the original body with a configured size cap and validates `X-Hub-Signature-256`.
3. Required delivery/event headers are validated and JSON is parsed.
4. A SQLite transaction inserts the delivery ID and full verified payload into a durable outbox. A unique key rejects duplicate deliveries.
5. Pull-request events receive a deterministic, explainable risk score in the webhook response.
6. n8n polls the authenticated outbox API and normalizes each event.
7. n8n calls the authenticated analysis endpoint. Deterministic risk is always available; optional AI advisory runs here, outside the GitHub request/response path.
8. n8n acknowledges the delivery only after the analysis step completes.

## Trust boundaries
- The webhook body and all event fields are untrusted input.
- The HMAC secret authenticates the sender; it does not make payload fields safe to execute.
- The integration bearer token authorizes n8n to read, analyze and acknowledge events; keep it separate from the GitHub webhook secret.
- Risk scores are heuristics, not security findings.
- AI summaries are advisory only and never authorize GitHub mutations.
- GitHub write operations are out of scope for the current milestone.

## Persistence
SQLite is the local development default. The unique delivery key and outbox row are written atomically and are safe for a single local process. Unacknowledged events remain pending and may be delivered more than once, so consumers must be idempotent. Multi-worker or multi-instance deployments should move to PostgreSQL with migrations and explicit transaction handling.
