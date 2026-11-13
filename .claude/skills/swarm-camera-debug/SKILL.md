---
name: swarm-camera-debug
description: Diagnose Swarm camera discovery, RTSP/ONVIF/HTTP/phone streams, person counting, stale frames and false alarms. Use for camera offline, threshold, reconnection or detector bugs.
---
# Camera debug
1. Read `AGENTS.md` and targeted `app/sources.py`, `app/detector.py`, `app/brands.py` and tests.
2. Classify the source type, count, freshness, detector mode, confirmation hits, threshold and cooldown; never record private IPs, credentials or real frames.
3. Reproduce with synthetic images and mocked streams. Check capture, model output, thresholds and alert separately.
4. Make a minimal patch with deterministic regression coverage; check timeouts, resources and reconnection.
5. Run `python -m pytest -q`, report exact results and mark untested hardware as **unverified**. Submit PR, don't merge.
