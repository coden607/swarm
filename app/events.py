"""Persistent alert history so alerts stay viewable after restarts and while offline."""
import json
import os
import threading
import time
from collections import deque
from pathlib import Path

_DATA = Path(os.getenv("SWARM_DATA_DIR", Path(__file__).resolve().parent.parent / "data"))
_FILE = _DATA / "events.json"
_lock = threading.Lock()
_events: deque = deque(maxlen=200)

try:
    _events.extend(json.loads(_FILE.read_text()))
except Exception:
    pass


def add(label: str, count: int, kind: str = "alert") -> None:
    with _lock:
        _events.append({"ts": time.time(), "kind": kind, "label": label or "all", "count": int(count)})
        try:
            _DATA.mkdir(parents=True, exist_ok=True)
            _FILE.write_text(json.dumps(list(_events)))
        except OSError:
            pass


def recent(n: int = 100) -> list:
    with _lock:
        return list(_events)[-n:][::-1]
