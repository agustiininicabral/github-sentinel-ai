# n8n integration

The API acts as the trusted GitHub webhook ingress. GitHub's signature is verified over the exact original request bytes by FastAPI; n8n receives only events already authenticated and persisted in the SQLite outbox. Do not point GitHub directly at an n8n Webhook node that parses and re-serializes the body before signature verification.

## Configure

1. Start Sentinel locally and set both `GITHUB_WEBHOOK_SECRET` and a separate high-entropy `SENTINEL_INTEGRATION_TOKEN` in `.env`.
2. Configure the GitHub repository webhook to call `https://YOUR-HTTPS-INGRESS/webhooks/github`, with content type `application/json`, the matching secret, and Pull requests events.
3. Make the Sentinel API reachable from the n8n host. If n8n runs in a container, `127.0.0.1` inside n8n refers to that container, not the Windows host; use a reachable host address and firewall rules.
4. In n8n, create an **HTTP Header Auth** credential named `Sentinel API Bearer`. Set the header name to `Authorization` and the value to `Bearer YOUR_SENTINEL_INTEGRATION_TOKEN`. Never place the token directly in a workflow export.
5. Import [github-sentinel-secure-intake.json](../n8n/github-sentinel-secure-intake.json).
6. Select the credential on all three HTTP Request nodes. If n8n assigns a new credential ID, reselect it on each node.
7. Test the workflow manually before activating the one-minute schedule.

## Workflow behavior

- Polls `GET /integrations/n8n/events?limit=25`.
- Splits the pending event batch into individual items.
- Normalizes event metadata while retaining the original verified payload for analysis.
- Calls `POST /integrations/n8n/analyze` with the delivery ID. Sentinel loads the event payload from its own outbox and returns deterministic PR risk plus an optional AI advisory.
- Acknowledges the delivery with `POST /integrations/n8n/events/{delivery_id}/ack` only after the analysis request completes.

The GitHub webhook response never waits for the AI provider. AI failures are reported as `ai_summary_status: unavailable`; deterministic risk remains available and the workflow can continue. The outbox is durable: a failed or unacknowledged item remains pending and is returned again. Consumers must therefore be idempotent. The acknowledgement endpoint is protected by the integration bearer token.

## API contract

- `GET /integrations/n8n/events?limit=25` — requires `Authorization: Bearer ...`; limit is 1–100.
- `POST /integrations/n8n/analyze` — requires the same token; body contains only `delivery_id` for a pending event.
- `POST /integrations/n8n/events/{delivery_id}/ack` — requires the same token; acknowledges one pending delivery.
- If `SENTINEL_INTEGRATION_TOKEN` is unset, the integration endpoints return 503.
- Never expose the integration endpoints without HTTPS and a strong token.

## Important deployment note

The included workflow uses `http://127.0.0.1:8000` as a local default. This works only when n8n and Sentinel share the same network namespace. Change the URL in all three HTTP Request nodes when they run on separate machines or in separate containers. Docker is not required by Sentinel itself; n8n's deployment method is independent.
