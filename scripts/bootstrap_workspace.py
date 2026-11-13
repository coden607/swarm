#!/usr/bin/env python3
"""Idempotent, no-network, local-only Swarm engineering memory bootstrap.

Does not touch .env, app state, cameras, services or external accounts.
An exclusive hard link publishes a fully-written new file without replacing
preexisting state, including under concurrent initializers.
"""
from __future__ import annotations

import argparse
import json
import os
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _write_once(path: Path, content: str) -> bool:
    if path.exists():
        return False
    fd, name = tempfile.mkstemp(prefix=".swarm.", suffix=".tmp", dir=path.parent)
    temp = Path(name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        try:
            os.link(temp, path)  # O_EXCL semantics: never overwrite a winner.
        except FileExistsError:
            return False
        return True
    finally:
        temp.unlink(missing_ok=True)


def bootstrap(root: Path, check_only: bool = False) -> dict[str, str]:
    root = Path(root)
    home = root / ".continuity" / "swarm"
    state = home / "state.json"
    events = home / "events.jsonl"
    if not check_only:
        home.mkdir(mode=0o700, parents=True, exist_ok=True)
        _write_once(state, json.dumps({"schema_version": 1, "facts": {}}, indent=2) + "\n")
        _write_once(events, "")
    if not state.is_file() or not events.is_file():
        raise RuntimeError("workspace not initialized; run --init")
    try:
        obj = json.loads(state.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise RuntimeError("invalid state.json; refusing to overwrite it") from exc
    if not isinstance(obj, dict) or obj.get("schema_version") != 1 or not isinstance(obj.get("facts"), dict):
        raise RuntimeError("state.json has an unexpected schema; refusing to overwrite it")
    try:
        with events.open(encoding="utf-8") as fh:
            for number, line in enumerate(fh, 1):
                if line.strip() and not isinstance(json.loads(line), dict):
                    raise RuntimeError(f"events.jsonl line {number} must be an object")
    except (OSError, ValueError) as exc:
        raise RuntimeError("invalid events.jsonl; refusing to overwrite it") from exc
    return {"state": "valid", "events": "valid"}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--init", action="store_true", help="create missing private memory files only")
    mode.add_argument("--check", action="store_true", help="validate only, without writing")
    parser.add_argument("--root", type=Path, default=ROOT, help="repo/worktree root")
    args = parser.parse_args()
    try:
        result = bootstrap(args.root, check_only=args.check)
    except RuntimeError as exc:
        parser.exit(1, f"FAIL: {exc}\n")
    print(f"PASS: private Swarm workspace ({result['state']}, {result['events']})")


if __name__ == "__main__":
    main()
