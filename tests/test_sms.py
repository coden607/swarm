"""Synthetic-only SMS outbox tests; zero provider network use."""
import sqlite3
from app import sms


def _setup(monkeypatch, path):
    monkeypatch.setattr(sms, "_DIR", path)
    monkeypatch.setenv("SWARM_SMS_TWILIO_SID", "AC" + "1" * 32)
    monkeypatch.setenv("SWARM_SMS_TWILIO_TOKEN", "TEST_ONLY")
    monkeypatch.setenv("SWARM_SMS_FROM", "+12025550101")
    monkeypatch.setenv("SWARM_SMS_TO", "+12025550102,+12025550103")


def test_disabled_no_file(monkeypatch, tmp_path):
    monkeypatch.setattr(sms, "_DIR", tmp_path)
    for k in ("SWARM_SMS_TWILIO_SID", "SWARM_SMS_TWILIO_TOKEN", "SWARM_SMS_FROM", "SWARM_SMS_TO"):
        monkeypatch.delenv(k, raising=False)
    assert sms.enqueue("synthetic alert") == 0
    assert sms.status() == {"sms_configured": False, "sms_pending": 0}
    assert not list(tmp_path.iterdir())


def test_retry_then_delivery(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    assert sms.enqueue("synthetic alert") == 2
    assert sms.status()["sms_pending"] == 2
    requests = []
    def unavailable(*args):
        requests.append(args)
        raise OSError("offline")
    monkeypatch.setattr(sms, "_send", unavailable)
    assert sms.drain_one() is False
    assert sms.status()["sms_pending"] == 2
    monkeypatch.setattr(sms, "_send", lambda *args: requests.append(args))
    assert sms.drain_one() is True
    with sqlite3.connect(tmp_path / "sms-outbox.sqlite3") as db:
        db.execute("UPDATE outbox SET next_attempt=0")
    assert sms.drain_one() is True
    assert sms.status()["sms_pending"] == 0
    assert len(requests) == 3


def test_invalid_recipient_no_enqueue(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    monkeypatch.setenv("SWARM_SMS_TO", "bad")
    assert sms.enqueue("alert") == 0
    assert not list(tmp_path.iterdir())


def test_status_excludes_private_information(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    sms.enqueue("synthetic alert")
    value = str(sms.status())
    assert "+1202555" not in value
    assert "synthetic alert" not in value
