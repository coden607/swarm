"""Opt-in durable Twilio SMS outbox; no frames, camera URLs, or keys are stored."""
import base64
import os
import sqlite3
import threading
import time
import urllib.parse
import urllib.request
from pathlib import Path

_DIR = Path(os.getenv("SWARM_DATA_DIR", Path(__file__).resolve().parents[1] / "data"))
_LOCK = threading.RLock()
_WAKE = threading.Event()
_STOP = threading.Event()
_THREAD = None
_CAP = 1000


def config():
    sid = os.getenv("SWARM_SMS_TWILIO_SID", "").strip()
    token = os.getenv("SWARM_SMS_TWILIO_TOKEN", "").strip()
    sender = os.getenv("SWARM_SMS_FROM", "").strip()
    recipients = tuple(dict.fromkeys(x.strip() for x in os.getenv("SWARM_SMS_TO", "").split(",") if x.strip()))
    if not (sid and token and sender and recipients):
        return None
    if len(sid) != 34 or not sid.startswith("AC") or not sid[2:].isalnum():
        return None
    if not all(v.startswith("+") and v[1:].isdigit() and 8 <= len(v) <= 16 for v in (sender, *recipients)):
        return None
    return sid, token, sender, recipients


def _db():
    _DIR.mkdir(mode=0o700, parents=True, exist_ok=True)
    db = sqlite3.connect(_DIR / "sms-outbox.sqlite3", timeout=10)
    db.execute("""CREATE TABLE IF NOT EXISTS outbox (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        recipient TEXT NOT NULL, message TEXT NOT NULL,
        next_attempt REAL NOT NULL, attempts INTEGER NOT NULL DEFAULT 0
    )""")
    return db


def enqueue(message: str):
    cfg = config()
    if cfg is None:
        return 0
    with _LOCK, _db() as db:
        if db.execute("SELECT COUNT(*) FROM outbox").fetchone()[0] + len(cfg[3]) > _CAP:
            raise RuntimeError("SMS queue full")
        now = time.time()
        db.executemany("INSERT INTO outbox(recipient,message,next_attempt) VALUES(?,?,?)",
                       [(number, message[:350], now) for number in cfg[3]])
    _WAKE.set()
    return len(cfg[3])


def _send(cfg, recipient, message):
    sid, token, sender, _ = cfg
    body = urllib.parse.urlencode({"From": sender, "To": recipient, "Body": message}).encode()
    auth = base64.b64encode((sid + ":" + token).encode()).decode()
    request = urllib.request.Request(
        "https://api.twilio.com/2010-04-01/Accounts/" + sid + "/Messages.json",
        data=body, method="POST",
        headers={"Authorization": "Basic " + auth, "Content-Type": "application/x-www-form-urlencoded"},
    )
    with urllib.request.urlopen(request, timeout=8) as response:
        if response.status not in (200, 201):
            raise RuntimeError("SMS provider non-success status")


def drain_one():
    cfg = config()
    if cfg is None:
        return False
    with _LOCK, _db() as db:
        row = db.execute("SELECT id,recipient,message,attempts FROM outbox WHERE next_attempt<=? ORDER BY id LIMIT 1",
                         (time.time(),)).fetchone()
        if row is None:
            return False
        ident, recipient, message, attempts = row
        # Claim before sending; network I/O never holds a DB transaction.
        db.execute("UPDATE outbox SET next_attempt=?,attempts=? WHERE id=?",
                   (time.time() + min(3600, 10 * 2 ** min(attempts, 8)), attempts + 1, ident))
    try:
        _send(cfg, recipient, message)
    except Exception:
        # Provider exceptions sometimes include phone numbers, request URLs or secrets.
        return False
    with _LOCK, _db() as db:
        db.execute("DELETE FROM outbox WHERE id=?", (ident,))
    return True


def status():
    if config() is None:
        return {"sms_configured": False, "sms_pending": 0}
    with _LOCK, _db() as db:
        count = db.execute("SELECT COUNT(*) FROM outbox").fetchone()[0]
    return {"sms_configured": True, "sms_pending": count}


def _worker():
    while not _STOP.is_set():
        if drain_one():
            continue
        _WAKE.wait(10)
        _WAKE.clear()


def start():
    global _THREAD
    if config() is None:
        return
    with _LOCK:
        if _THREAD and _THREAD.is_alive():
            return
        _STOP.clear()
        _THREAD = threading.Thread(target=_worker, daemon=True, name="swarm-sms")
        _THREAD.start()


def stop():
    _STOP.set()
    _WAKE.set()
