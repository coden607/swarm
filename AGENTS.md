# Swarm — AI agent instructions

## Mission
Swarm is a **camera people-counting and crowd alert product**, not an AI-agent swarm runtime. Do not add face recognition, individual identity tracking, biometric profiling or unrelated agent features.

Read `MISSION.md`, `FACTORY_RULES.md`, `harness/END-TO-END.md` and then this file before changing code. Never edit those protected files, `harness/harness.config.json` or `.factory/holdout/`. Human approval controls merges, production, and secrets.

## Code map
- `app/main.py`: FastAPI login, JWT, cameras, frames, status, snapshot, health.
- `app/sources.py` / `app/brands.py`: RTSP, ONVIF, HTTP, USB and phone input.
- `app/detector.py`: HOG/YOLOX local counts, optional Gemini, debounce/cooldown.
- `app/storage.py`, `app/events.py`, `app/push.py`, `app/alert.py`: persistence and alerts.
- `ui/`: PWA; `android/` and `ios/`: mobile clients.
- `install.sh` / `install.ps1`: system setup; `tests/` and `.github/workflows/ci.yml`: verification.

## Development loop
1. Check current branch, commit SHA and open PRs. Make an evidence-based small plan.
2. Route through ContinuityOS when installed and verified. Select only relevant skills from `github.com/coden607/skills` and `.claude/skills/`. Never claim a router, tool, plugin or MCP is connected without checking.
3. Work on one isolated branch/worktree. Prefer deterministic local scripts and synthetic camera fixtures. No real camera data goes to an LLM by default.
4. Add regression tests for changed behavior. Run `python -m pytest -q`; run the relevant GitHub Actions jobs for installers, native builds, OpenCV and platform concerns. Report exact results; do not infer device success from a build.
5. For auth, networking, camera, Gemini, push, installer or remote-access changes, complete a privacy/security review.
6. Produce a scoped PR with evidence, failures, unknowns and rollback. **Never auto-merge, force-push, deploy, sign, pay, send, or access protected secrets.** Stop after three attempts at the same blocker.

## Protected data and defaults
No `.env` contents, API keys, password-bearing camera URLs, private IP inventories, JPEG/video frames, push endpoints or full transcripts in prompts, PRs, logs, memory or external providers. Use redacted metadata and synthetic frames. `SWARM_DETECTOR=auto` may transmit frames to Gemini when configured; `SWARM_REMOTE=1` exposes a public tunnel. Development baseline: `SWARM_DETECTOR=local` and `SWARM_REMOTE=0`.

## Handoff
Report verified result → checks with exit codes → risk or blocker → next authorized action. State unknowns explicitly. Detailed guidance: `docs/agent-workspace.md`, `docs/agent-memory.md`, `docs/integrations.md`, `docs/environment.md`.
