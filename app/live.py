"""In-process alarm fan-out. No network. Open dashboards on the LAN hear a swarm immediately."""
from __future__ import annotations

import asyncio
import threading
import time

_lock = threading.Lock()
_queues: set = set()
_loop = None
_recent = None
_recent_at = 0.0
RECENT_S = 30


def bind(loop) -> None:
    global _loop
    _loop = loop


def subscribe():
    q = asyncio.Queue(maxsize=16)
    with _lock:
        _queues.add(q)
    return q


def unsubscribe(q) -> None:
    with _lock:
        _queues.discard(q)


def recent():
    with _lock:
        if _recent is not None and time.time() - _recent_at <= RECENT_S:
            return dict(_recent)
    return None


def publish(event: dict) -> None:
    """Remember the alarm and wake every open dashboard. Must not raise."""
    global _recent, _recent_at
    payload = dict(event)
    with _lock:
        _recent = payload
        _recent_at = time.time()
        queues = list(_queues)
        loop = _loop
    if loop is None or not queues:
        return

    def _fanout() -> None:
        for q in queues:
            try:
                q.put_nowait(payload)
            except asyncio.QueueFull:
                pass

    try:
        loop.call_soon_threadsafe(_fanout)
    except RuntimeError:
        pass


async def wait(q, timeout: float = 15):
    try:
        return await asyncio.wait_for(q.get(), timeout)
    except asyncio.TimeoutError:
        return None
