---
applyTo: "app/**/*.py,tests/**/*.py"
---
Protect FastAPI authentication and login endpoints, credential-bearing camera URLs, outbound Gemini calls, local data paths and push subscriptions. Use synthetic JPEGs, bounded timeouts, proper camera-thread cleanup and deterministic tests. Keep atomic writes through `app/storage.py`; don't accidentally run cloud inference in tests. Test auth, reconnection, stale counts and debounce for relevant edits. Run `python -m pytest -q`, distinguishing passing tests from unavailable hardware. See `docs/security-review.md`.
