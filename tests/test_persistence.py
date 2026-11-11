"""State files must remain readable when a replacement fails."""
import json
import os
from pathlib import Path

import pytest


@pytest.fixture(params=["settings", "push", "events"])
def state_writer(request, monkeypatch, tmp_path):
    # Keep all application state out of the checkout, even when run alone.
    monkeypatch.setenv("SWARM_DATA_DIR", str(tmp_path))
    if request.param == "settings":
        from app import main
        path = tmp_path / "settings.json"
        write = lambda: main._write(path, {"total_threshold": 8})
    elif request.param == "push":
        from app import push
        path = tmp_path / "push.json"
        monkeypatch.setattr(push, "_DATA", tmp_path)
        monkeypatch.setattr(push, "SUB_FILE", path)
        write = lambda: push._write([{"endpoint": "https://push.example/new"}])
    else:
        from app import events
        path = tmp_path / "events.json"
        monkeypatch.setattr(events, "_DATA", tmp_path)
        monkeypatch.setattr(events, "_FILE", path)
        write = lambda: events.add("test", 5)
    path.write_text('["previous state"]')
    return path, write


def test_replacement_failure_preserves_state(state_writer, monkeypatch):
    path, write = state_writer
    attempted = []

    def fail_replace(source, destination):
        attempted.append(source)
        assert Path(destination) == path
        assert json.loads(path.read_text()) == ["previous state"]
        raise OSError("simulated disk failure")

    monkeypatch.setattr(os, "replace", fail_replace)
    try:
        write()
    except OSError:
        pass  # Event logging deliberately tolerates disk errors.
    assert attempted, "state must be published with an atomic replacement"
    assert json.loads(path.read_text()) == ["previous state"]
    assert list(path.parent.iterdir()) == [path]


def test_replacement_publishes_complete_private_json(state_writer, monkeypatch):
    path, write = state_writer
    replace = os.replace
    attempted = []

    def inspect_replace(source, destination):
        source = Path(source)
        attempted.append(source)
        assert source.parent == path.parent
        assert json.loads(path.read_text()) == ["previous state"]
        assert json.loads(source.read_text())
        if os.name != "nt":
            assert source.stat().st_mode & 0o777 == 0o600
        replace(source, destination)

    monkeypatch.setattr(os, "replace", inspect_replace)
    write()
    assert attempted, "the old file must stay intact until replacement"
    assert json.loads(path.read_text()) != ["previous state"]
    assert list(path.parent.iterdir()) == [path]


@pytest.mark.parametrize("failure", ["serialization", "flush"])
def test_failed_staging_preserves_state(tmp_path, monkeypatch, failure):
    from app.storage import write_json

    path = tmp_path / "cameras.json"
    path.write_text('{"camera": "saved"}')
    value = {"camera": "new"}
    error = TypeError
    if failure == "serialization":
        value["invalid"] = object()
    else:
        error = OSError

        def fail_sync(fd):
            raise OSError("simulated flush failure")

        monkeypatch.setattr(os, "fsync", fail_sync)
    with pytest.raises(error):
        write_json(path, value)
    assert json.loads(path.read_text()) == {"camera": "saved"}
    assert list(tmp_path.iterdir()) == [path]
