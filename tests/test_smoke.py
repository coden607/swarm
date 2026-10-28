import http.server
import os
import tempfile
import threading
import time

import cv2
import numpy as np
import pytest

os.environ["SWARM_DATA_DIR"] = tempfile.mkdtemp()
os.environ["ADMIN_PASS"] = "testpass"
os.environ["JWT_SECRET"] = "x" * 32
os.environ["SWARM_ALERT_COOLDOWN"] = "0"
os.environ["SWARM_SERVER_SOUND"] = "0"
os.environ.pop("GEMINI_API_KEY", None)


from app.detector import HogCounter  # noqa: E402

REAL_COUNT = HogCounter.count


@pytest.fixture(scope="module", autouse=True)
def fake_count():
    mp = pytest.MonkeyPatch()
    mp.setattr(HogCounter, "count", lambda self, f: 5)
    yield
    mp.undo()


@pytest.fixture(scope="module")
def jpeg():
    img = np.full((360, 640, 3), 90, np.uint8)
    return cv2.imencode(".jpg", img)[1].tobytes()


@pytest.fixture(scope="module")
def snapshot_server(jpeg):
    class H(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path.startswith("/snapshot.jpg"):
                self.send_response(200); self.send_header("Content-Type", "image/jpeg"); self.end_headers(); self.wfile.write(jpeg)
            else:
                self.send_response(404); self.end_headers()
        def log_message(self, *a): pass
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield srv.server_address[1]
    srv.shutdown()


@pytest.fixture(scope="module")
def client(tmp_path_factory):
    from fastapi.testclient import TestClient
    from app.main import app
    with TestClient(app) as c:
        t = c.post("/login", params={"username": "admin", "password": "testpass"}).json()["access_token"]
        c.headers["Authorization"] = f"Bearer {t}"
        yield c


def wait(fn, timeout=20):
    end = time.time() + timeout
    while time.time() < end:
        v = fn()
        if v:
            return v
        time.sleep(0.3)
    return None


def test_candidates():
    from app.sources import candidates
    c = candidates("192.168.1.5", "admin", "p@ss", "hikvision")
    assert c[0] == "rtsp://admin:p%40ss@192.168.1.5:554/Streaming/Channels/101"
    assert any(u.startswith("http://admin:p%40ss@192.168.1.5:8080/") for u in c)
    assert candidates("0") == ["0"]
    assert candidates("rtsp://h/x/y") == ["rtsp://h/x/y"]
    assert len(candidates("10.0.0.2")) > 30


def test_auth_required(client):
    assert client.get("/cameras", headers={"Authorization": ""}).status_code == 401
    assert client.get("/health").json()["status"] == "ok"


def test_hog_runs_on_blank(jpeg):
    img = cv2.imdecode(np.frombuffer(jpeg, np.uint8), cv2.IMREAD_COLOR)
    assert REAL_COUNT(HogCounter(), img) == 0


def test_snapshot_camera_autodetect_and_alarm(client, snapshot_server):
    r = client.post("/cameras/snap", json={"url": f"127.0.0.1:{snapshot_server}", "threshold": 3})
    assert r.status_code == 200
    s = wait(lambda: next((c for c in client.get("/status").json()["cameras"] if c["id"] == "snap" and c["count"] == 5), None), 60)
    assert s, client.get("/status").json()
    assert s["alarm"] and "snapshot.jpg" in s["resolved"]
    assert client.get("/status").json()["alarm"] is True
    assert client.put("/cameras/snap/threshold", json={"threshold": 9}).status_code == 200
    assert wait(lambda: client.get("/status").json()["cameras"][0]["alarm"] is False)


def test_phone_camera_and_combined_threshold(client, jpeg):
    client.put("/settings", json={"total_threshold": 8})
    assert client.post("/cameras/ph", json={"url": "phone", "threshold": 99}).status_code == 200
    def total():
        client.post("/cameras/ph/frame", content=jpeg, headers={"Content-Type": "image/jpeg"})
        return client.get("/status").json()
    st = wait(lambda: (lambda s: s if s["total"] >= 10 else None)(total()))
    assert st and st["total_alarm"] is True        # 5 (snap) + 5 (phone) >= 8, though each camera < its own threshold
    assert client.post("/cameras/snap/frame", content=jpeg).status_code == 400


def test_local_auto_login(client):
    from fastapi.testclient import TestClient
    from app.main import app
    assert client.get("/local-token").status_code == 403                      # LAN-style client
    with TestClient(app, client=("127.0.0.1", 5000)) as local:
        assert local.get("/local-token").status_code == 200
        assert local.get("/local-token", headers={"cf-connecting-ip": "1.2.3.4"}).status_code == 403  # via tunnel


def test_xmeye_template_gets_credentials():
    from app.sources import candidates
    assert any("user=admin&password=pw" in u for u in candidates("10.0.0.9", "admin", "pw"))


def test_live_snapshot(client, snapshot_server):
    client.post("/cameras/live", json={"url": f"127.0.0.1:{snapshot_server}", "threshold": 99})
    r = wait(lambda: (lambda x: x if x.status_code == 200 else None)(client.get("/cameras/live/snapshot")), 60)
    assert r and r.headers["content-type"] == "image/jpeg" and r.content[:2] == b"\xff\xd8"
    assert client.get("/cameras/nope/snapshot").status_code == 404
    client.delete("/cameras/live")


def test_push_subscribe_and_send(client, monkeypatch):
    pytest.importorskip("pywebpush")
    k = client.get("/push/key").json()["key"]
    assert len(k) > 80                                             # uncompressed P-256 point, base64url
    sub = {"endpoint": "https://push.example/abc", "keys": {"p256dh": "x", "auth": "y"}}
    assert client.post("/push/subscribe", json=sub).json()["devices"] == 1
    assert client.post("/push/subscribe", json=sub).json()["devices"] == 1   # deduped
    assert client.post("/push/subscribe", json={"endpoint": "x"}).status_code == 400
    import pywebpush
    from app import push
    sent = []
    monkeypatch.setattr(pywebpush, "webpush", lambda info, data, **kw: sent.append((info["endpoint"], data)))
    push.send_all("Swarm alert", "7 people")
    assert sent and sent[0][0] == sub["endpoint"] and "7 people" in sent[0][1]


def test_events_and_remote(client):
    ev = client.get("/events").json()["events"]
    assert ev and ev[0]["count"] >= 5                      # alarms were logged
    assert client.get("/remote").json() == {"enabled": False, "url": None}


def test_login_throttle(client):
    codes = [client.post("/login", params={"username": "admin", "password": "bad"}).status_code for _ in range(7)]
    assert codes[:5] == [401] * 5 and codes[-1] == 429


def test_persistence_and_delete(client):
    from app import main
    assert "snap" in main.CAM_FILE.read_text()
    assert client.delete("/cameras/snap").status_code == 200
    assert client.delete("/cameras/ph").status_code == 200
    assert client.delete("/cameras/nope").status_code == 404
    assert "snap" not in main.CAM_FILE.read_text()
