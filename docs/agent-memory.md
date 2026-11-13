# Swarm second brain: current STATE and dated EVENT

No real surveillance data belongs in AI memory.

## Location
- STATE: `.continuity/swarm/state.json`, local and gitignored; one current value per key.
- EVENT: `.continuity/swarm/events.jsonl`, local and gitignored; append-only dated evidence.
- KNOWLEDGE: concise verified lessons in a reviewed PR/document, source-linked by SHA.
- SESSION HANDOFF: current SHA, worktree, last tests, pending PR, blocker and next action.

These files are not automatically created or synchronized by this document. `.continuity/` is already gitignored.

## Schema
STATE keys can include `base_sha`, `branch`, `open_pr`, `next_action`, `blockers`, `test_matrix` and `last_verified_ci`. For each fact retain source and `checked_at`. EVENT lines should have `timestamp`, `kind`, `source`, `detail_redacted` and `verification`.

Current fact changed? **Replace** the old STATE value, never accumulate duplicates. Something happened? **Append** a dated EVENT. If both apply, do both. Reconcile against live GitHub before assertions. Prefer unknown to unsupported guesses. Preserve distinct historical failures.

## Forbidden memory material
Camera/video/snapshot pixels, real person's identity, location/device/IP inventories, user credentials, JWTs, passwords in camera URLs, push endpoints, full transcripts, private .env or data JSON. Keep only abstract counters and redacted, authorized diagnostic summaries. No third-party memory/vector/RAG sink without an explicit privacy design and owner permission.

## Session steps
Start by reading governance, commit SHA and relevant state. Record significant verified events during work. Finish by updating one authoritative current state value per key, appending events and reporting the exact tests and blockers. Don't claim a memory write unless it was actually verified.
