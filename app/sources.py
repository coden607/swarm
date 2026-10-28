"""Turn "whatever the user typed" into a stream of frames.

Accepts: IP/hostname (auto-probes ~40 common RTSP/HTTP paths for most brands),
full rtsp:// http(s):// URLs (MJPEG or single-JPEG snapshot endpoints), USB
webcam index ("0" / "usb:0"), a video file path, or frames pushed by a browser.
"""
from __future__ import annotations

import os
import re
import socket
import threading
import time
import urllib.request
import uuid
from concurrent.futures import ThreadPoolExecutor
from typing import List, Optional, Tuple
from urllib.parse import quote, unquote, urlparse

import cv2
import numpy as np

os.environ.setdefault("OPENCV_FFMPEG_CAPTURE_OPTIONS", "rtsp_transport;tcp|timeout;5000000|stimeout;5000000")

# (brand tag, path) - tag only changes ordering when the user picks a brand
RTSP_PATHS = [
    ("hikvision", "Streaming/Channels/101"), ("hikvision", "Streaming/Channels/1"),
    ("dahua", "cam/realmonitor?channel=1&subtype=0"), ("amcrest", "cam/realmonitor?channel=1&subtype=1"),
    ("tapo", "stream1"), ("tapo", "stream2"),
    ("reolink", "h264Preview_01_main"), ("reolink", "Preview_01_main"),
    ("axis", "axis-media/media.amp"),
    ("unifi", "live/ch0"), ("foscam", "videoMain"), ("generic", "live"),
    ("generic", "live/main"), ("generic", "h264"), ("generic", "stream"), ("generic", "1"), ("generic", "11"),
    ("generic", "cam1/h264"), ("generic", "onvif1"), ("generic", "MediaInput/h264"), ("generic", "av0_0"), ("generic", ""),
]
HTTP_PATHS = [
    "video.mjpg", "mjpg/video.mjpg", "videostream.cgi", "video", "stream.mjpg", "mjpeg", "?action=stream",
    "snapshot.jpg", "cgi-bin/snapshot.cgi", "image/jpeg.cgi", "shot.jpg", "axis-cgi/jpg/image.cgi",
    "tmpfs/auto.jpg", "?action=snapshot", "image.jpg",
]
SNAP_RE = re.compile(r"(snapshot|shot\.jpg|image/jpeg|jpeg\.cgi|image\.jpg|auto\.jpg|\.jpe?g|image\.cgi|action=snapshot)", re.I)


# ----------------------------------------------------------------- candidates
def candidates(addr: str, user: str = "", pw: str = "", brand: str = "generic") -> List[str]:
    addr = (addr or "").strip()
    if not addr:
        return []
    if addr.isdigit() or addr.startswith("usb:") or os.path.exists(addr):
        return [addr]
    cred = f"{quote(user, safe='')}:{quote(pw, safe='')}@" if user else ""
    out: List[str] = []
    schemes = {"rtsp", "http"}
    port: Optional[int] = None
    if "://" in addr:
        p = urlparse(addr)
        out.append(addr if (not user or p.username) else addr.replace("://", "://" + cred, 1))
        if p.path not in ("", "/") or p.query:
            return out
        host, port, schemes = p.hostname or "", p.port, {p.scheme.replace("https", "http")}
    else:
        hp = addr.split("/")[0]
        host, _, ps = hp.partition(":")
        port = int(ps) if ps.isdigit() else None
    rt = sorted(RTSP_PATHS, key=lambda t: t[0] != brand)  # stable: chosen brand first
    if "rtsp" in schemes:
        out += [f"rtsp://{cred}{host}:{port or 554}/{path}" for _, path in rt]
    if "http" in schemes:
        for hp_ in ([port] if port else [80, 8080]):
            out += [f"http://{cred}{host}:{hp_}/{path}" for path in HTTP_PATHS]
    return list(dict.fromkeys(out))


# -------------------------------------------------------------------- sources
def _split_creds(url: str) -> Tuple[str, str, str]:
    p = urlparse(url)
    netloc = (p.hostname or "") + (f":{p.port}" if p.port else "")
    return p._replace(netloc=netloc).geturl(), unquote(p.username or ""), unquote(p.password or "")


def _fetch_jpeg(url: str, user: str = "", pw: str = "", timeout: float = 4.0):
    try:
        handlers = []
        if user:
            mgr = urllib.request.HTTPPasswordMgrWithDefaultRealm()
            mgr.add_password(None, url, user, pw)
            handlers = [urllib.request.HTTPBasicAuthHandler(mgr), urllib.request.HTTPDigestAuthHandler(mgr)]
        data = urllib.request.build_opener(*handlers).open(url, timeout=timeout).read(8_000_000)
        img = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)
        return img
    except Exception:
        return None


class CvSource:
    """Anything cv2.VideoCapture can open: RTSP, MJPEG over HTTP, USB, files."""

    def __init__(self, target):
        self.cap = cv2.VideoCapture(target)
        self._first = None

    def first_frame(self) -> bool:
        for _ in range(6):
            if not self.cap.isOpened():
                return False
            ok, f = self.cap.read()
            if ok and f is not None:
                self._first = f
                return True
            time.sleep(0.3)
        return False

    def read(self):
        if self._first is not None:
            f, self._first = self._first, None
            return f
        ok, f = self.cap.read()
        return f if ok else None

    def close(self):
        try:
            self.cap.release()
        except Exception:
            pass


class SnapshotSource:
    """Cameras that only expose a single-JPEG URL: poll it."""

    def __init__(self, url: str, user: str = "", pw: str = ""):
        self.url, self.user, self.pw = url, user, pw
        self._last = 0.0

    def read(self):
        wait = 0.5 - (time.time() - self._last)
        if wait > 0:
            time.sleep(wait)
        self._last = time.time()
        return _fetch_jpeg(self.url, self.user, self.pw)

    def close(self):
        pass


class PushSource:
    """Frames posted by a browser/phone running the PWA."""

    def __init__(self):
        self._frame = None
        self._lock = threading.Lock()

    def put(self, frame):
        with self._lock:
            self._frame = frame

    def read(self):
        with self._lock:
            f, self._frame = self._frame, None
        if f is None:
            time.sleep(0.2)
        return f

    def close(self):
        pass


def _reachable(host: str, port: int, timeout: float = 2.0) -> bool:
    try:
        with socket.create_connection((host, port), timeout):
            return True
    except OSError:
        return False


def _try(c: str):
    if c.isdigit() or c.startswith("usb:") or os.path.exists(c):
        src = CvSource(int(c.split(":")[-1]) if not os.path.exists(c) else c)
        if src.first_frame():
            return src
        src.close()
        return None
    p = urlparse(c)
    port = p.port or {"rtsp": 554, "http": 80, "https": 443}.get(p.scheme, 0)
    if p.hostname and port and not _reachable(p.hostname, port):
        return None
    if p.scheme in ("http", "https") and SNAP_RE.search(p.path + ("?" + p.query if p.query else "")):
        clean, u, pw = _split_creds(c)
        return SnapshotSource(clean, u, pw) if _fetch_jpeg(clean, u, pw) is not None else None
    src = CvSource(c)
    if src.first_frame():
        return src
    src.close()
    return None


def open_first(addr: str, user: str = "", pw: str = "", brand: str = "generic") -> Tuple[Optional[object], str]:
    """Return (source, resolved_url). Tries candidates in priority order, in parallel."""
    cands = candidates(addr, user, pw, brand)
    if not cands:
        return None, "empty address"
    ex = ThreadPoolExecutor(max_workers=8)
    futs = [ex.submit(_try, c) for c in cands]
    winner, url = None, ""

    def _close_late(fu):
        try:
            r = fu.result()
            if r is not None:
                r.close()
        except Exception:
            pass

    for c, f in zip(cands, futs):
        if winner is not None:  # already have the best-priority hit: drop the rest
            if not f.cancel():
                f.add_done_callback(_close_late)
            continue
        try:
            winner, url = f.result(), c
        except Exception:
            winner = None
    ex.shutdown(wait=False)
    if winner is None and user and "://" not in addr and not addr.isdigit():
        try:  # last resort: ask the camera itself via ONVIF for its stream URI
            from .brands import _discover_onvif_rtsp
            uri = _discover_onvif_rtsp(addr.split(":")[0].split("/")[0], user, pw)
            if uri:
                uri = uri.replace("://", f"://{quote(user, safe='')}:{quote(pw, safe='')}@", 1)
                winner, url = _try(uri), uri
        except Exception:
            winner = None
    if winner is None:
        return None, f"no working stream found at {addr} (tried {len(cands)} addresses; check IP, user/password, and that RTSP/ONVIF is enabled on the camera)"
    return winner, _mask(url)


def _mask(url: str) -> str:
    return re.sub(r"//[^/@]*@", "//***@", url)


# ------------------------------------------------------------------ discovery
def local_ip() -> str:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("10.255.255.255", 1))
        return s.getsockname()[0]
    except OSError:
        return "127.0.0.1"


_PROBE = (
    '<?xml version="1.0" encoding="UTF-8"?><e:Envelope xmlns:e="http://www.w3.org/2003/05/soap-envelope" '
    'xmlns:w="http://schemas.xmlsoap.org/ws/2004/08/addressing" xmlns:d="http://schemas.xmlsoap.org/ws/2005/04/discovery" '
    'xmlns:dn="http://www.onvif.org/ver10/network/wsdl"><e:Header><w:MessageID>uuid:%s</w:MessageID>'
    "<w:To>urn:schemas-xmlsoap-org:ws:2005:04:discovery</w:To>"
    "<w:Action>http://schemas.xmlsoap.org/ws/2005/04/discovery/Probe</w:Action></e:Header>"
    "<e:Body><d:Probe><d:Types>dn:NetworkVideoTransmitter</d:Types></d:Probe></e:Body></e:Envelope>"
)


def _ws_discovery(timeout: float = 3.0) -> set:
    found = set()
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.settimeout(0.5)
        s.sendto((_PROBE % uuid.uuid4()).encode(), ("239.255.255.250", 3702))
        end = time.time() + timeout
        while time.time() < end:
            try:
                data, addr = s.recvfrom(65535)
            except socket.timeout:
                continue
            found.add(addr[0])
    except OSError:
        pass
    finally:
        s.close()
    return found


def discover() -> list:
    """ONVIF WS-Discovery + RTSP/MJPEG port scan of the local /24."""
    ip = local_ip()
    prefix = ip.rsplit(".", 1)[0]
    ports = (554, 8554, 8080)
    hosts = {}

    def probe(h):
        op = [p for p in ports if _reachable(h, p, 0.4)]
        return h, op

    with ThreadPoolExecutor(max_workers=128) as ex:
        scan = ex.submit(_ws_discovery)
        for h, op in ex.map(probe, [f"{prefix}.{i}" for i in range(1, 255) if f"{prefix}.{i}" != ip]):
            if op:
                hosts[h] = {"ip": h, "ports": op, "onvif": False}
        for h in scan.result():
            hosts.setdefault(h, {"ip": h, "ports": [], "onvif": True})["onvif"] = True
    for v in hosts.values():
        v["hint"] = "ONVIF camera" if v["onvif"] else ("RTSP camera" if set(v["ports"]) & {554, 8554} else "maybe phone 'IP Webcam' app")
    return sorted(hosts.values(), key=lambda v: tuple(int(x) for x in v["ip"].split(".")))
