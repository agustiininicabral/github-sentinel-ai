# Security model

- Use a high-entropy webhook secret and store it only in an environment variable or secret manager.
- Require HTTPS at the public ingress.
- Verify the HMAC over the exact raw bytes before parsing JSON.
- Reject missing or malformed signatures and required delivery headers.
- Keep webhook endpoints rate-limited and bounded by request size at the ingress.
- Treat event payloads, PR titles, descriptions and labels as untrusted data.
- Never execute shell commands or interpolate payload text into SQL.
- Do not let an AI-generated summary trigger merges, approvals, pushes or permission changes.
- Use a GitHub App with least-privilege permissions when API access is introduced.
- Rotate secrets immediately if they are exposed.
- SQLite mode is intended for local/single-instance operation, not horizontally scaled production.
