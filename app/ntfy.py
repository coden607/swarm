"""Free phone alarm through a local ntfy server. No account and no per-message fee."""
from __future__ import annotations

import os
import secrets
import socket
import threading
import urllib.error
import urllib.request
from pathlib import Path

_DATA = Path(os.getenv("SWARM_DATA_DIR", Path(__file__).resolve().parents[1] / "data"))
_TOPIC = _DATA / "ntfy-topic"


def enabled() -> bool:
    return os.getenv("SWARM_NTFY", "").strip() == "1"


def _topic() -> str:
    _DATA.mkdir(mode=0o700, parents=True, exist_ok=True)
    try:
        name = _TOPIC.read_text(encoding="utf-8").strip()
    except OSError:
        name = ""
    if not name or "/" in name or len(name) > 64:
        name = "swarm-" + secrets.token_hex(16)
        _TOPIC.write_text(name, encoding="utf-8")
        try:
            _TOPIC.chmod(0o600)
        except OSError:
            pass
    return name


def server() -> str:
    return os.getenv("SWARM_NTFY_URL", "http://127.0.0.1:2586").rstrip("/")


def _lan() -> str:
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.connect(("192.0.2.1", 1))
        return sock.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        sock.close()


def subscribe_url() -> str:
    """Address a phone on this Wi-Fi uses. Localhost is rewritten to the LAN address."""
    if not enabled():
        return ""
    base = os.getenv("SWARM_NTFY_PUBLIC", "").strip().rstrip("/") or server()
    if "127.0.0.1" in base or "localhost" in base:
        base = "http://" + _lan() + ":2586"
    return base + "/" + _topic()


def publish(message: str) -> bool:
    if not enabled():
        return False
    request = urllib.request.Request(
        server() + "/" + _topic(),
        data=message.encode()[:350],
        method="POST",
        headers={"Title": "Swarm", "Priority": "5", "Tags": "warning"},
    )
    try:
        with urllib.request.urlopen(request, timeout=1.0) as response:
            return response.status in (200, 201)
    except (OSError, urllib.error.URLError):
        return False


def publish_async(message: str) -> None:
    if enabled():
        threading.Thread(target=publish, args=(message,), daemon=True).start()


def status() -> dict:
    return {"ntfy_enabled": enabled(), "ntfy_subscribe": subscribe_url()}
