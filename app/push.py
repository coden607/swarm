"""Web Push so iPhones/Android get swarm alerts even when the app is closed (needs https + app on Home Screen)."""
import base64
import json
import os
import threading
import time
from pathlib import Path

from .storage import write_json

_DATA = Path(os.getenv("SWARM_DATA_DIR", Path(__file__).resolve().parent.parent / "data"))
KEY_FILE, SUB_FILE = _DATA / "vapid_private.pem", _DATA / "push.json"
OUTBOX = _DATA / "push-outbox.json"
_drainer = None
CLAIM_SUB = os.getenv("SWARM_PUSH_SUB", "https://github.com/coden607/swarm")
_lock = threading.Lock()


def _vapid():
    from py_vapid import Vapid
    _DATA.mkdir(parents=True, exist_ok=True)
    if KEY_FILE.exists():
        return Vapid.from_file(str(KEY_FILE))
    v = Vapid()
    v.generate_keys()
    v.save_key(str(KEY_FILE))
    try:
        KEY_FILE.chmod(0o600)
    except OSError:
        pass
    return v


def public_key() -> str:
    from cryptography.hazmat.primitives import serialization as ser
    raw = _vapid().public_key.public_bytes(ser.Encoding.X962, ser.PublicFormat.UncompressedPoint)
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def subscriptions() -> list:
    try:
        return json.loads(SUB_FILE.read_text())
    except Exception:
        return []


def _write(subs: list) -> None:
    _DATA.mkdir(parents=True, exist_ok=True)
    write_json(SUB_FILE, subs)


def add(sub: dict) -> None:
    with _lock:
        subs = [s for s in subscriptions() if s.get("endpoint") != sub.get("endpoint")]
        subs.append(sub)
        _write(subs)


def remove(endpoint: str) -> None:
    with _lock:
        _write([s for s in subscriptions() if s.get("endpoint") != endpoint])


def _read_outbox() -> list:
    try:
        return json.loads(OUTBOX.read_text())
    except Exception:
        return []


def pending() -> int:
    return len(_read_outbox())


def _save_outbox(items: list) -> None:
    _DATA.mkdir(parents=True, exist_ok=True)
    write_json(OUTBOX, items[-100:])


def _remember(sub: dict, title: str, body: str) -> None:
    with _lock:
        items = [i for i in _read_outbox() if not (i.get("sub", {}).get("endpoint") == sub.get("endpoint") and i.get("body") == body)]
        items.append({"sub": sub, "title": title, "body": body, "attempts": 0, "next": time.time()})
        _save_outbox(items)


def _deliver(webpush, webpush_exc, sub: dict, title: str, body: str):
    """Return 'ok', 'gone', or 'retry'. Network errors stay retryable."""
    try:
        webpush(sub, json.dumps({"title": title, "body": body}), vapid_private_key=str(KEY_FILE), vapid_claims={"sub": CLAIM_SUB})
        return "ok"
    except webpush_exc as e:
        code = getattr(getattr(e, "response", None), "status_code", None)
        print(f"[push] failed ({code})")
        return "gone" if code in (404, 410) else "retry"
    except Exception as e:
        print(f"[push] error: {e}")
        return "retry"


def send_all(title: str, body: str) -> None:
    subs = subscriptions()
    if not subs:
        return
    try:
        from pywebpush import WebPushException, webpush
    except ImportError:
        print("[push] pywebpush not installed; phone alerts disabled")
        return
    _vapid()
    for sub in subs:
        result = _deliver(webpush, WebPushException, sub, title, body)
        if result == "gone":
            remove(sub.get("endpoint", ""))
        elif result == "retry":
            _remember(sub, title, body)


def drain() -> None:
    """Resend Web Push messages that failed while the network was down."""
    try:
        from pywebpush import WebPushException, webpush
    except ImportError:
        return
    now = time.time()
    with _lock:
        due = [i for i in _read_outbox() if i.get("next", 0) <= now]
        rest = [i for i in _read_outbox() if i.get("next", 0) > now]
        if not due:
            return
        _save_outbox(rest)
    try:
        _vapid()
    except Exception as e:
        print(f"[push] retry keys unavailable: {e}")
        with _lock:
            _save_outbox(_read_outbox() + due)
        return
    failed = []
    for item in due:
        sub = item.get("sub") or {}
        result = _deliver(webpush, WebPushException, sub, item.get("title") or "Swarm alert", item.get("body") or "")
        if result == "gone":
            remove(sub.get("endpoint", ""))
        elif result == "retry":
            attempts = int(item.get("attempts", 0)) + 1
            item["attempts"] = attempts
            item["next"] = time.time() + min(3600, 10 * 2 ** min(attempts, 8))
            failed.append(item)
    if failed:
        with _lock:
            _save_outbox(_read_outbox() + failed)


def _drain_loop() -> None:
    while True:
        try:
            drain()
        except Exception as e:
            print(f"[push] retry failed: {e}")
        time.sleep(5)


def start() -> None:
    global _drainer
    with _lock:
        if _drainer and _drainer.is_alive():
            return
        _drainer = threading.Thread(target=_drain_loop, daemon=True, name="swarm-push")
        _drainer.start()


def send_async(title: str, body: str) -> None:
    threading.Thread(target=send_all, args=(title, body), daemon=True).start()
