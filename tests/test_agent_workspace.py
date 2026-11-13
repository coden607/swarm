"""Tests for the optional no-network engineering-memory bootstrap."""
import json
import os
from pathlib import Path

import pytest

from scripts.bootstrap_workspace import bootstrap


def test_init_is_private_and_idempotent(tmp_path):
    assert bootstrap(tmp_path) == {"state": "valid", "events": "valid"}
    home = tmp_path / ".continuity" / "swarm"
    state, events = home / "state.json", home / "events.jsonl"
    obj = json.loads(state.read_text())
    assert obj == {"schema_version": 1, "facts": {}}
    assert events.read_text() == ""
    if os.name != "nt":
        assert state.stat().st_mode & 0o777 == 0o600
        assert events.stat().st_mode & 0o777 == 0o600
    events.write_text('{"timestamp":"2026-11-11","kind":"synthetic-test"}\n')
    state.write_text('{"schema_version":1,"facts":{"branch":{"value":"test"}}}')
    s_mtime, e_mtime = state.stat().st_mtime_ns, events.stat().st_mtime_ns
    assert bootstrap(tmp_path) == {"state": "valid", "events": "valid"}
    assert state.stat().st_mtime_ns == s_mtime
    assert events.stat().st_mtime_ns == e_mtime
    assert json.loads(state.read_text())["facts"]["branch"]["value"] == "test"
    assert "synthetic-test" in events.read_text()


def test_check_does_not_create_files(tmp_path):
    with pytest.raises(RuntimeError, match="not initialized"):
        bootstrap(tmp_path, check_only=True)
    assert not (tmp_path / ".continuity").exists()


def test_invalid_state_is_preserved(tmp_path):
    bootstrap(tmp_path)
    state = tmp_path / ".continuity" / "swarm" / "state.json"
    state.write_text("{broken")
    with pytest.raises(RuntimeError, match="refusing to overwrite"):
        bootstrap(tmp_path)
    assert state.read_text() == "{broken"


def test_invalid_event_is_preserved(tmp_path):
    bootstrap(tmp_path)
    events = tmp_path / ".continuity" / "swarm" / "events.jsonl"
    events.write_text("[123]\n")
    with pytest.raises(RuntimeError, match="line 1"):
        bootstrap(tmp_path, check_only=True)
    assert events.read_text() == "[123]\n"
