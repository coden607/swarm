"""Free ntfy alarm. No server and no network."""
import urllib.error

from app import ntfy


def test_off_by_default(monkeypatch):
    monkeypatch.delenv("SWARM_NTFY", raising=False)
    assert ntfy.publish("synthetic") is False
    assert ntfy.status()["ntfy_subscribe"] == ""


def test_publish_uses_local_server(monkeypatch, tmp_path):
    monkeypatch.setenv("SWARM_NTFY", "1")
    monkeypatch.setenv("SWARM_NTFY_URL", "http://127.0.0.1:2586")
    monkeypatch.setattr(ntfy, "_DATA", tmp_path)
    monkeypatch.setattr(ntfy, "_TOPIC", tmp_path / "ntfy-topic")
    seen = {}

    class Resp:
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    def capture(request, timeout):
        seen["url"] = request.full_url
        seen["priority"] = request.get_header("Priority")
        seen["timeout"] = timeout
        seen["body"] = request.data
        return Resp()

    monkeypatch.setattr(ntfy.urllib.request, "urlopen", capture)
    assert ntfy.publish("synthetic alert") is True
    assert seen["url"].startswith("http://127.0.0.1:2586/swarm-")
    assert seen["priority"] == "5"
    assert seen["timeout"] == 1.0
    assert b"synthetic alert" in seen["body"]
    assert ntfy.status()["ntfy_subscribe"].startswith("http://")
    assert "127.0.0.1" not in ntfy.status()["ntfy_subscribe"]


def test_publish_failure_is_quiet(monkeypatch, tmp_path):
    monkeypatch.setenv("SWARM_NTFY", "1")
    monkeypatch.setattr(ntfy, "_DATA", tmp_path)
    monkeypatch.setattr(ntfy, "_TOPIC", tmp_path / "ntfy-topic")

    def down(request, timeout):
        raise urllib.error.URLError("offline")

    monkeypatch.setattr(ntfy.urllib.request, "urlopen", down)
    assert ntfy.publish("synthetic alert") is False
