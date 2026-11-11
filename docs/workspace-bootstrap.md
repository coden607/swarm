# Optional local Swarm workspace bootstrap

The PR defines memory policy but cannot create files on your local machine or change ChatGPT Project settings. This opt-in tool creates **only** two local, gitignored engineering-memory files and never opens the network, reads a camera, touches .env, installs packages or starts services.

From a checked-out Swarm worktree:

```sh
python scripts/bootstrap_workspace.py --init
python scripts/bootstrap_workspace.py --check
```

Creates:
- `.continuity/swarm/state.json` — single source for current STATE, schema `{"schema_version": 1, "facts": {}}`.
- `.continuity/swarm/events.jsonl` — empty append-only EVENT log.

Initialization is atomic/exclusive per file, idempotent and Ctrl-C-safe: preexisting records are not overwritten. If a record is corrupt or not the supported schema, it stops rather than resetting it. On filesystems without hard-link support, creation fails safely; no silent unsafe fallback. The directory already falls under the repository's `.continuity/` gitignore rule.

The bootstrap is **not** a memory daemon, automatic cloud sync or MCP server. Agents may update the private files only within the source/date/redaction rules of [agent-memory.md](agent-memory.md). Never place real camera data or credentials there. To test the bootstrap independently:

```sh
python -m pytest -q tests/test_agent_workspace.py
```
