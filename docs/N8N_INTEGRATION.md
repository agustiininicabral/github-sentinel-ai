# n8n integration (planned)

The current API verifies GitHub's HMAC using the original request bytes. A generic n8n Webhook -> HTTP Request workflow that parses and re-serializes JSON will change those bytes and invalidate the signature.

Recommended safe patterns:
1. Point GitHub directly at Sentinel's HTTPS ingress and let Sentinel verify the signature before any workflow dispatch; or
2. Put a trusted raw-body-preserving gateway in front of both systems and verify the signature there before forwarding a normalized, authenticated event.

Do not disable signature verification to make an n8n workflow work. Do not forward a parsed JSON body and claim it preserves GitHub's signature. Add human approval before any future GitHub write operation.
