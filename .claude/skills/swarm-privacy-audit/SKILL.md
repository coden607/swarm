---
name: swarm-privacy-audit
description: Review Swarm security and privacy for camera credentials, local-token, network discovery, Gemini frame export, public tunnels, mobile app tokens and push delivery.
---
# Privacy audit
1. Read `AGENTS.md`, `docs/security-review.md` and the relevant code.
2. Map data boundary: loopback, LAN, public tunnel, optional Gemini, browser, mobile device and local storage.
3. Inspect auth, source URL redaction, JWTs, proxy headers, state permissions, image export and installer defaults.
4. Use static evidence plus synthetic tests, not owner's private images or credentials.
5. Report **confirmed by source**, **reproduced**, **plausible but untested**, or **unknown**. Propose least-privilege fixes in a PR. Don't enable remote access, rotate production keys, or merge.
