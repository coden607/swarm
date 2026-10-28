"""Web Push so iPhones/Android get swarm alerts even when the app is closed (needs https + app on Home Screen)."""
import base64
import json
import os
import threading
from pathlib import Path

_DATA = Path(os.getenv("SWARM_DATA_DIR", Path(__file__).resolve().parent.parent / "data"))
KEY_FILE, SUB_FILE = _DATA / "vapid_private.pem", _DATA / "push.json"
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
    SUB_FILE.write_text(json.dumps(subs))
    try:
        SUB_FILE.chmod(0o600)
    except OSError:
        pass


def add(sub: dict) -> None:
    with _lock:
        subs = [s for s in subscriptions() if s.get("endpoint") != sub.get("endpoint")]
        subs.append(sub)
        _write(subs)


def remove(endpoint: str) -> None:
    with _lock:
        _write([s for s in subscriptions() if s.get("endpoint") != endpoint])


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
        try:
            webpush(sub, json.dumps({"title": title, "body": body}), vapid_private_key=str(KEY_FILE), vapid_claims={"sub": CLAIM_SUB})
        except WebPushException as e:
            code = getattr(getattr(e, "response", None), "status_code", None)
            print(f"[push] failed ({code}): {e}")
            if code in (404, 410):
                remove(sub.get("endpoint", ""))
        except Exception as e:
            print(f"[push] error: {e}")


def send_async(title: str, body: str) -> None:
    threading.Thread(target=send_all, args=(title, body), daemon=True).start()
