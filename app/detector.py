import os
import threading
import time

import cv2
import numpy as np

from .alert import trigger_alert
from .sources import PushSource, open_first

COOLDOWN = float(os.getenv("SWARM_ALERT_COOLDOWN", "60"))
STALE_AFTER = 15.0


class HogCounter:
    """Offline person counter (OpenCV HOG+SVM). No key, no internet.
    Best on upright people at moderate distance; dense crowds are under-counted."""

    def __init__(self):
        self.h = cv2.HOGDescriptor()
        self.h.setSVMDetector(cv2.HOGDescriptor_getDefaultPeopleDetector())

    def count(self, frame) -> int:
        w = frame.shape[1]
        if w > 960:
            frame = cv2.resize(frame, None, fx=960 / w, fy=960 / w)
        rects, weights = self.h.detectMultiScale(frame, winStride=(8, 8), padding=(8, 8), scale=1.05)
        if len(rects) == 0:
            return 0
        boxes = [[int(x), int(y), int(a), int(b)] for x, y, a, b in rects]
        keep = cv2.dnn.NMSBoxes(boxes, [float(s) for s in np.ravel(weights)], 0.3, 0.4)
        return int(len(np.array(keep).flatten())) if len(keep) else 0


class GeminiCounter:
    def __init__(self, key: str, model: str):
        import google.generativeai as genai
        genai.configure(api_key=key)
        self.model = genai.GenerativeModel(model)

    def count(self, frame) -> int:
        w = frame.shape[1]
        if w > 960:
            frame = cv2.resize(frame, None, fx=960 / w, fy=960 / w)
        _, buf = cv2.imencode(".jpg", frame)
        r = self.model.generate_content([
            "Count every distinct person visible in this image, including partially visible and distant people. Respond with only an integer.",
            {"mime_type": "image/jpeg", "data": buf.tobytes()},
        ])
        return int("".join(c for c in r.text if c.isdigit()))


class Counter:
    """auto: Gemini when GEMINI_API_KEY is set and reachable, otherwise local HOG."""

    def __init__(self):
        mode = os.getenv("SWARM_DETECTOR", "auto").lower()
        key = os.getenv("GEMINI_API_KEY", "")
        self.local = HogCounter()
        self.remote = None
        self.skip_until = 0.0
        if mode != "local" and key:
            try:
                self.remote = GeminiCounter(key, os.getenv("GEMINI_MODEL", "gemini-2.0-flash"))
            except Exception as e:
                print(f"[detector] Gemini unavailable ({e}); using local detector")

    @property
    def name(self) -> str:
        return "gemini" if self.remote else "local"

    @property
    def interval(self) -> float:
        return 2.0 if self.remote else 1.0

    def count(self, frame) -> int:
        if self.remote and time.time() >= self.skip_until:
            try:
                return self.remote.count(frame)
            except Exception as e:
                print(f"[detector] Gemini error ({e}); local fallback for 30s")
                self.skip_until = time.time() + 30
        return self.local.count(frame)


class CameraProcessor:
    def __init__(self, cam_id: str, spec: dict, on_count=None):
        self.id = cam_id
        self.spec = spec
        self.on_count = on_count
        self.stop_event = threading.Event()
        self.thread = threading.Thread(target=self._process, daemon=True)
        self.is_push = spec.get("brand") == "phone"
        self.push = PushSource() if self.is_push else None
        self.counter = None
        self.count = 0
        self.updated = 0.0
        self.last_alert = 0.0
        self.resolved = ""
        self.status = "starting"

    # -- public view
    url = property(lambda s: s.spec["url"])
    brand = property(lambda s: s.spec.get("brand", "generic"))
    threshold = property(lambda s: s.spec["threshold"])

    @threshold.setter
    def threshold(self, v):
        self.spec["threshold"] = int(v)

    def fresh(self) -> bool:
        return time.time() - self.updated < STALE_AFTER

    @property
    def alarm(self) -> bool:
        return self.fresh() and self.count >= self.threshold

    def push_frame(self, jpeg: bytes) -> bool:
        if not self.push:
            return False
        img = cv2.imdecode(np.frombuffer(jpeg, np.uint8), cv2.IMREAD_COLOR)
        if img is None:
            return False
        self.push.put(img)
        return True

    def run(self):
        self.thread.start()

    def stop(self):
        self.stop_event.set()
        if self.thread.is_alive():
            self.thread.join(timeout=5)

    # -- worker
    def _process(self):
        try:
            self.counter = Counter()
        except Exception as e:
            self.status = f"error: {e}"
            return
        backoff = 2
        while not self.stop_event.is_set():
            if self.is_push:
                src = self.push
                self.status = "waiting for phone frames"
            else:
                self.status = "connecting"
                src, res = open_first(self.spec["url"], self.spec.get("username", ""), self.spec.get("password", ""), self.brand)
                if src is None:
                    self.status = f"offline: {res}"
                    self.stop_event.wait(backoff)
                    backoff = min(backoff * 2, 60)
                    continue
                self.resolved = res
                backoff = 2
            last_ok, last_inf = time.time(), 0.0
            while not self.stop_event.is_set():
                frame = src.read()
                if frame is None:
                    if not self.is_push and time.time() - last_ok > STALE_AFTER:
                        self.status = "stream lost, reconnecting"
                        break
                    continue
                last_ok = time.time()
                if last_ok - last_inf < self.counter.interval:
                    continue
                last_inf = last_ok
                try:
                    n = self.counter.count(frame)
                except Exception as e:
                    self.status = f"error: {e}"
                    continue
                self.count, self.updated = n, time.time()
                self.status = f"running ({self.counter.name})"
                if self.on_count:
                    self.on_count(self)
                if n >= self.threshold and time.time() - self.last_alert > COOLDOWN:
                    self.last_alert = time.time()
                    trigger_alert(n, self.spec.get("alert_email_addresses", []), self.id)
            if not self.is_push:
                src.close()
