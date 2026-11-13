# Swarm privacy and security: initial source review

These are **observations and tests to prioritize**, not a completed penetration test.

## Verified by reading the current code
1. `app/detector.py` sends JPEG frame bytes to Gemini in `GeminiCounter.count` when cloud inference is used. `auto` with a key can select that mode. Development should explicitly set `SWARM_DETECTOR=local`.
2. `app/main.py` launches a Cloudflare quick tunnel when `SWARM_REMOTE=1`. Login still applies, but a public network path is created.
3. `install.sh` starts Uvicorn bound to `0.0.0.0`. Public-tunnel-off alone does not prevent LAN access.
4. `app/main.py` returns camera `url` and `resolved` fields to authenticated clients; treat them as possibly credential-bearing, particularly when debugging.
5. `GET /local-token` trusts loopback client addresses only when selected proxy headers are absent. Reverse-proxy scenarios deserve explicit tests.
6. `app/storage.py` atomically saves JSON; `app/push.py` stores private VAPID material and subscriptions on disk. These still require file/directory access control.

## Proposed, not yet verified
- Prove URL redaction across API/error/log/output and deny unexpected credential exposure.
- Test proxy-header and local-token behavior through every supported reverse proxy.
- Review URL/source validation and discovery network boundaries.
- Test JWT expiry, login rate limiting and privacy-preserving error responses.
- Prove no outbound Gemini calls in local-only mode.
- Test push subscription retention, network TLS and authorized mobile clients.
- Confirm UI cache and event retention policy; get device-level validation.

Label each claim **source-observed**, **reproduced**, **plausible**, or **unverified**. Use synthetic fixtures, not owner images. Keep security remediation separate from these workspace documents and require human sign-off for auth or public-exposure changes.
