import asyncio
import base64
import hashlib
import json
import os
import re
import secrets
import shutil
import subprocess
import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Dict, List
from xml.sax.saxutils import escape

import jwt
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi.staticfiles import StaticFiles
from starlette.middleware.gzip import GZipMiddleware
from pydantic import BaseModel, Field

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

from . import events, live, ntfy, push, sms  # noqa: E402
from .alert import trigger_alert  # noqa: E402
from .detector import COOLDOWN, CONFIRM_HITS, CameraProcessor  # noqa: E402
from .health import health_check  # noqa: E402
from .sources import discover  # noqa: E402
from .storage import write_json  # noqa: E402

DATA = Path(os.getenv("SWARM_DATA_DIR", ROOT / "data"))
DATA.mkdir(parents=True, exist_ok=True)
CAM_FILE, SET_FILE = DATA / "cameras.json", DATA / "settings.json"

JWT_SECRET = os.getenv("JWT_SECRET") or secrets.token_hex(32)  # random per-run if unset
ADMIN_USER = os.getenv("ADMIN_USER", "admin")
ADMIN_PASS = os.getenv("ADMIN_PASS", "")
TOKEN_TTL = int(float(os.getenv("SWARM_TOKEN_DAYS", "30")) * 86400)  # stay signed in on paired devices

cameras: Dict[str, CameraProcessor] = {}
settings = {"total_threshold": 0}  # 0 = combined-swarm alert off
_state = {"last_total_alert": 0.0, "above_since": 0.0}


def _write(path: Path, obj) -> None:
    write_json(path, obj)


def _save() -> None:
    _write(CAM_FILE, {cid: p.spec for cid, p in cameras.items()})
    _write(SET_FILE, settings)


def fresh_total() -> int:
    return sum(p.count for p in cameras.values() if p.fresh())


def _over_total() -> bool:
    t = settings["total_threshold"]
    return t > 0 and fresh_total() >= t


def total_alarm() -> bool:
    """Combined swarm only after the count stays high, same bar as a single camera."""
    if not _over_total() or not _state["above_since"]:
        return False
    return time.time() - _state["above_since"] >= max(0, CONFIRM_HITS - 1)


def on_count(_proc) -> None:
    now = time.time()
    if _over_total():
        _state["above_since"] = _state["above_since"] or now
        if total_alarm() and now - _state["last_total_alert"] > COOLDOWN:
            _state["last_total_alert"] = now
            emails = sorted({e for p in cameras.values() for e in p.spec.get("alert_email_addresses", [])})
            trigger_alert(fresh_total(), emails, "all cameras combined")
    else:
        _state["above_since"] = 0.0


def _start(cid: str, spec: dict) -> CameraProcessor:
    p = CameraProcessor(cid, spec, on_count)
    cameras[cid] = p
    p.run()
    return p


_tunnel = {"proc": None}


def _start_tunnel() -> None:
    """SWARM_REMOTE=1: expose the dashboard on a public https URL via cloudflared (login still required)."""
    if os.getenv("SWARM_REMOTE") != "1":
        return
    exe = ROOT / "bin" / ("cloudflared.exe" if os.name == "nt" else "cloudflared")
    exe = str(exe) if exe.exists() else shutil.which("cloudflared")
    if not exe:
        print("[remote] cloudflared not found; remote access disabled")
        return
    scheme, port = os.getenv("SWARM_SCHEME", "http"), os.getenv("SWARM_PORT", "8000")
    cmd = [exe, "tunnel", "--no-autoupdate", "--url", f"{scheme}://localhost:{port}"]
    if scheme == "https":
        cmd.append("--no-tls-verify")
    log = open(DATA / "tunnel.log", "w")
    _tunnel["proc"] = subprocess.Popen(cmd, stdout=log, stderr=subprocess.STDOUT)


@asynccontextmanager
async def lifespan(_app):
    live.bind(asyncio.get_running_loop())
    _start_tunnel()
    sms.start()
    push.start()
    try:
        settings.update(json.loads(SET_FILE.read_text()))
    except Exception:
        pass
    try:
        for cid, spec in json.loads(CAM_FILE.read_text()).items():
            _start(cid, spec)
    except Exception:
        pass
    yield
    sms.stop()
    for p in list(cameras.values()):
        p.stop_event.set()
    if _tunnel["proc"]:
        _tunnel["proc"].terminate()


app = FastAPI(title="Swarm Detection Service", lifespan=lifespan)
app.add_middleware(GZipMiddleware, minimum_size=500)
bearer = HTTPBearer(auto_error=False)


class CameraConfig(BaseModel):
    url: str = Field(..., description="IP/host, rtsp://, http:// (MJPEG or snapshot), USB index like 0, or 'phone'")
    brand: str = "generic"
    username: str = ""
    password: str = ""
    threshold: int = Field(10, ge=1, description="People count that triggers an alert")
    alert_email_addresses: List[str] = Field(default_factory=list)


class Threshold(BaseModel):
    threshold: int = Field(..., ge=1)


class Settings(BaseModel):
    total_threshold: int = Field(..., ge=0, description="Combined people across all cameras; 0 disables")


def require_auth(cred: HTTPAuthorizationCredentials = Depends(bearer)) -> str:
    if cred is None:
        raise HTTPException(status_code=401, detail="Missing token")
    try:
        return jwt.decode(cred.credentials, JWT_SECRET, algorithms=["HS256"])["sub"]
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")


_fails: Dict[str, List[float]] = {}


@app.post("/login")
async def login(request: Request, username: str = "", password: str = ""):
    if request.headers.get("content-type", "").split(";")[0].strip() == "application/json":
        try:
            data = await request.json()
        except Exception:
            data = {}
        if isinstance(data, dict):
            username = str(data.get("username") or username or "")
            password = str(data.get("password") if data.get("password") is not None else password)
    if not ADMIN_PASS:
        raise HTTPException(status_code=503, detail="ADMIN_PASS not set in .env")
    ip = request.headers.get("cf-connecting-ip") or (request.client.host if request.client else "?")
    now = time.time()
    recent = [t for t in _fails.get(ip, []) if now - t < 60]
    if len(recent) >= 5:
        raise HTTPException(status_code=429, detail="Too many attempts; wait a minute")
    def _same(left: str, right: str) -> bool:
        return secrets.compare_digest(hashlib.sha256(left.encode()).digest(), hashlib.sha256(right.encode()).digest())

    ok = _same(username, ADMIN_USER) and _same(password, ADMIN_PASS)
    if not ok:
        _fails[ip] = recent + [now]
        raise HTTPException(status_code=401, detail="Bad credentials")
    token = jwt.encode({"sub": username, "exp": int(time.time()) + TOKEN_TTL}, JWT_SECRET, algorithm="HS256")
    return {"access_token": token}


@app.get("/local-token")
def local_token(request: Request):
    """Auto sign-in for a browser running on the server machine itself (never via LAN/tunnel)."""
    host = request.client.host if request.client else ""
    proxied = any(h in request.headers for h in ("cf-connecting-ip", "x-forwarded-for", "x-real-ip", "forwarded"))
    if host not in ("127.0.0.1", "::1") or proxied:
        raise HTTPException(status_code=403, detail="local only")
    token = jwt.encode({"sub": ADMIN_USER, "exp": int(time.time()) + TOKEN_TTL}, JWT_SECRET, algorithm="HS256")
    return {"access_token": token}


@app.get("/health")
def health():
    return health_check()


@app.post("/cameras/{camera_id}")
def add_camera(camera_id: str, config: CameraConfig, _: str = Depends(require_auth)):
    if camera_id in cameras:
        raise HTTPException(status_code=400, detail="Camera ID already exists")
    spec = config.model_dump(mode="json")
    if config.url.strip().lower() == "phone":
        spec["brand"] = "phone"
    _start(camera_id, spec)
    _save()
    return {"status": "added", "camera_id": camera_id}


@app.put("/cameras/{camera_id}/threshold")
def set_threshold(camera_id: str, body: Threshold, _: str = Depends(require_auth)):
    p = cameras.get(camera_id)
    if not p:
        raise HTTPException(status_code=404, detail="Camera not found")
    p.threshold = body.threshold
    _save()
    return {"status": "updated", "camera_id": camera_id, "threshold": body.threshold}


@app.put("/settings")
def set_settings(body: Settings, _: str = Depends(require_auth)):
    settings["total_threshold"] = body.total_threshold
    _save()
    return settings


@app.delete("/cameras/{camera_id}")
def remove_camera(camera_id: str, _: str = Depends(require_auth)):
    p = cameras.pop(camera_id, None)
    if not p:
        raise HTTPException(status_code=404, detail="Camera not found")
    p.stop()
    _save()
    return {"status": "removed", "camera_id": camera_id}


@app.post("/cameras/{camera_id}/frame")
async def post_frame(camera_id: str, request: Request, _: str = Depends(require_auth)):
    p = cameras.get(camera_id)
    if not p:
        raise HTTPException(status_code=404, detail="Camera not found")
    if not p.push_frame(await request.body()):
        raise HTTPException(status_code=400, detail="Not a phone camera or bad JPEG")
    return {"ok": True}


@app.get("/cameras")
def list_cameras(_: str = Depends(require_auth)):
    return {"cameras": [{"id": cid, "url": p.url, "brand": p.brand, "threshold": p.threshold} for cid, p in cameras.items()]}


@app.get("/status")
def status(_: str = Depends(require_auth)):
    return {
        "cameras": [
            {"id": cid, "url": p.url, "resolved": p.resolved, "brand": p.brand, "threshold": p.threshold,
             "count": p.count if p.fresh() else None, "status": p.status, "alarm": p.alarm}
            for cid, p in cameras.items()
        ],
        "total": fresh_total(),
        "total_threshold": settings["total_threshold"],
        "total_alarm": total_alarm(),
        "alarm": total_alarm() or any(p.alarm for p in cameras.values()),
    }


@app.get("/cameras/{camera_id}/snapshot")
def snapshot(camera_id: str, _: str = Depends(require_auth)):
    p = cameras.get(camera_id)
    if not p:
        raise HTTPException(status_code=404, detail="Camera not found")
    jpg = p.snapshot_jpeg()
    if jpg is None:
        raise HTTPException(status_code=404, detail="No frame yet")
    return Response(jpg, media_type="image/jpeg", headers={"Cache-Control": "no-store"})


@app.get("/push/key")
def push_key(_: str = Depends(require_auth)):
    try:
        return {"key": push.public_key()}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Push unavailable: {e}")


@app.post("/push/subscribe")
def push_subscribe(sub: dict, _: str = Depends(require_auth)):
    if not sub.get("endpoint") or "keys" not in sub:
        raise HTTPException(status_code=400, detail="Bad subscription")
    push.add(sub)
    return {"ok": True, "devices": len(push.subscriptions())}


def _sse(obj) -> str:
    return "data: " + json.dumps(obj) + "\n\n"


@app.get("/alerts/live")
async def alerts_live(once: int = 0, _: str = Depends(require_auth)):
    """LAN alarm stream. Manual SSE so Python 3.9's older FastAPI pin still starts.

    once=1 returns the latest alarm and closes. The dashboard leaves it off and stays connected.
    """
    q = live.subscribe()

    async def gen():
        try:
            recent = live.recent()
            if recent:
                yield _sse(recent)
            yield _sse({"ready": True})
            if once:
                return
            while True:
                item = await live.wait(q, 15)
                yield ": keepalive\n\n" if item is None else _sse(item)
        finally:
            live.unsubscribe(q)

    return StreamingResponse(
        gen(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.get("/alerts/delivery")
def alert_delivery(_: str = Depends(require_auth)):
    state = sms.status()
    state["push_pending"] = push.pending()
    state["server_sound"] = os.getenv("SWARM_SERVER_SOUND", "1") == "1"
    state["local_hook"] = bool(os.getenv("SWARM_LOCAL_HOOK", "").strip())
    state.update(ntfy.status())
    return state


@app.get("/events")
def get_events(_: str = Depends(require_auth)):
    return {"events": events.recent(100)}


@app.get("/remote")
def remote(_: str = Depends(require_auth)):
    url = None
    try:
        m = re.search(r"https://[a-z0-9-]+\.trycloudflare\.com", (DATA / "tunnel.log").read_text())
        url = m.group(0) if m else None
    except OSError:
        pass
    return {"enabled": os.getenv("SWARM_REMOTE") == "1", "url": url}


@app.get("/discover")
def discover_cameras(_: str = Depends(require_auth)):
    return {"devices": discover()}


def _install_origin(request: Request) -> str:
    proto = (request.headers.get("x-forwarded-proto") or request.url.scheme).split(",")[0].strip()
    host = (request.headers.get("x-forwarded-host") or request.headers.get("host") or request.url.netloc).split(",")[0].strip()
    return f"{proto}://{host}".rstrip("/")


def _webclip_icon() -> str:
    try:
        return base64.b64encode((ROOT / "ui" / "apple-touch-icon.png").read_bytes()).decode("ascii")
    except OSError:
        return ""


@app.get("/install")
def install_page():
    """Phone installer. No login, so an iPhone can open it before the dashboard is set up."""
    return FileResponse(ROOT / "installer.html", media_type="text/html")


@app.api_route("/install.mobileconfig", methods=["GET", "HEAD"])
def install_mobileconfig(request: Request):
    """One-tap iPhone Home Screen icon. Safari opens Settings; the user taps Install."""
    origin = _install_origin(request)
    clip_uid = str(uuid.uuid5(uuid.NAMESPACE_URL, origin + "/swarm-webclip"))
    prof_uid = str(uuid.uuid5(uuid.NAMESPACE_URL, origin + "/swarm-profile"))
    tag = clip_uid.split("-")[0]
    icon = _webclip_icon()
    icon_xml = f"<key>Icon</key><data>{icon}</data>" if icon else ""
    body = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>PayloadContent</key>
  <array>
    <dict>
      <key>FullScreen</key>
      <true/>
      {icon_xml}
      <key>IsRemovable</key>
      <true/>
      <key>Label</key>
      <string>Swarm</string>
      <key>PayloadDescription</key>
      <string>Swarm Detection</string>
      <key>PayloadDisplayName</key>
      <string>Swarm</string>
      <key>PayloadIdentifier</key>
      <string>com.coden607.swarm.webclip.{tag}</string>
      <key>PayloadType</key>
      <string>com.apple.webClip.managed</string>
      <key>PayloadUUID</key>
      <string>{clip_uid}</string>
      <key>PayloadVersion</key>
      <integer>1</integer>
      <key>Precomposed</key>
      <true/>
      <key>URL</key>
      <string>{escape(origin)}/</string>
    </dict>
  </array>
  <key>PayloadDisplayName</key>
  <string>Swarm</string>
  <key>PayloadIdentifier</key>
  <string>com.coden607.swarm.{tag}</string>
  <key>PayloadOrganization</key>
  <string>Swarm Detection</string>
  <key>PayloadRemovalDisallowed</key>
  <false/>
  <key>PayloadType</key>
  <string>Configuration</string>
  <key>PayloadUUID</key>
  <string>{prof_uid}</string>
  <key>PayloadVersion</key>
  <integer>1</integer>
</dict>
</plist>
"""
    return Response(
        content=body,
        media_type="application/x-apple-aspen-config",
        headers={
            "Content-Disposition": 'inline; filename="swarm.mobileconfig"',
            "Cache-Control": "no-store",
        },
    )


# Static UI last so it never shadows API routes
app.mount("/", StaticFiles(directory=str(ROOT / "ui"), html=True), name="ui")
