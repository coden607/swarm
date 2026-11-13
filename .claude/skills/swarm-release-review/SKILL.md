---
name: swarm-release-review
description: Verify Swarm PR readiness, Python/OpenCV tests, PWA behavior, installers and Android/iOS builds before human approval.
---
# Release review
1. Read `MISSION.md`, `FACTORY_RULES.md` and `harness/END-TO-END.md`. Never edit protected paths.
2. Match changed paths to checks: Python 3.9–3.13, OpenCV 5, Linux/macOS/Windows/iSH installers, Android APK, iOS simulator and unsigned IPA.
3. Run locally available tests and inspect GitHub Actions for the exact SHA. Report every failing, skipped, unknown and passing check.
4. Require privacy review for camera, auth, push, remote or installer networking edits; flag native physical-device checks for human testing.
5. Prepare evidence and rollback for human sign-off; no merge, publish, signing or production deployment.
