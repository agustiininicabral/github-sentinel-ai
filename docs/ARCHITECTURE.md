# Architecture

## Runtime flow
1. GitHub sends an event to `POST /webhooks/github`.
2. FastAPI reads the original body bytes and validates `X-Hub-Signature-256`.
3. Required delivery/event headers are validated and JSON is parsed.
4. A SQLite unique key prevents a delivery from being processed twice.
5. Pull-request events receive a deterministic, explainable risk score.
6. The API returns an acknowledgement. Future n8n workflows can consume this response.

## Trust boundaries
- The webhook body and all event fields are untrusted input.
- The HMAC secret authenticates the sender; it does not make payload fields safe to execute.
- Risk scores are heuristics, not security findings.
- AI summaries are advisory only.
- GitHub write operations are out of scope for the current MVP.

## Persistence
SQLite is the local development default. Its unique delivery key is atomic and safe for a single local process. Multi-worker or multi-instance deployments should move to PostgreSQL with migrations and explicit transaction handling.
