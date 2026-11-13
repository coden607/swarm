"""Local alarm fan-out. No camera, no network."""
import json


def test_local_fanout_runs_before_disk_and_push(monkeypatch):
    from app.alert import trigger_alert
    order = []
    monkeypatch.setattr("app.live.publish", lambda event: order.append(("live", event["label"])))
    monkeypatch.setattr("app.events.add", lambda *args: order.append("disk"))
    monkeypatch.setattr("app.push.send_async", lambda *args: order.append("push"))
    monkeypatch.setattr("app.sms.enqueue", lambda *args: order.append("sms"))
    monkeypatch.setenv("SWARM_SERVER_SOUND", "0")
    monkeypatch.delenv("SWARM_LOCAL_HOOK", raising=False)
    trigger_alert(3, [], "door")
    assert order[0] == ("live", "door")
    assert order.index("disk") < order.index("push")


def test_local_hook_is_not_a_shell(monkeypatch):
    from app.alert import trigger_alert
    started = []
    monkeypatch.setattr("app.alert.subprocess.Popen", lambda cmd, **kwargs: started.append(cmd))
    monkeypatch.setattr("app.live.publish", lambda event: None)
    monkeypatch.setattr("app.events.add", lambda *args: None)
    monkeypatch.setattr("app.push.send_async", lambda *args: None)
    monkeypatch.setattr("app.sms.enqueue", lambda *args: None)
    monkeypatch.setenv("SWARM_SERVER_SOUND", "0")
    monkeypatch.setenv("SWARM_LOCAL_HOOK", "/usr/bin/true --siren")
    trigger_alert(2, [], "yard")
    assert started[0][:3] == ["/usr/bin/true", "--siren", "Swarm alert on yard: 2 people detected."]


def test_push_outbox_retries_after_network_loss(monkeypatch, tmp_path):
    from app import push
    monkeypatch.setattr(push, "_DATA", tmp_path)
    monkeypatch.setattr(push, "SUB_FILE", tmp_path / "push.json")
    monkeypatch.setattr(push, "OUTBOX", tmp_path / "push-outbox.json")
    monkeypatch.setattr(push, "KEY_FILE", tmp_path / "vapid_private.pem")
    sub = {"endpoint": "https://push.example/abc", "keys": {"p256dh": "x", "auth": "y"}}
    push.add(sub)
    monkeypatch.setattr(push, "_vapid", lambda: None)

    def offline(*args, **kwargs):
        raise OSError("offline")

    import pywebpush
    monkeypatch.setattr(pywebpush, "webpush", offline)
    push.send_all("Swarm alert", "4 people")
    saved = json.loads((tmp_path / "push-outbox.json").read_text())
    assert saved[0]["body"] == "4 people"
    sent = []
    monkeypatch.setattr(pywebpush, "webpush", lambda info, data, **kwargs: sent.append(info["endpoint"]))
    assert push.drain() is None
    assert sent == ["https://push.example/abc"]
    assert push.pending() == 0
