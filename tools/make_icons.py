"""Generate PWA / iOS / Windows icons into ui/. Usage: python tools/make_icons.py"""
import pathlib
import struct

import cv2
import numpy as np

OUT = pathlib.Path(__file__).resolve().parent.parent / "ui"
GREEN = (62, 138, 43)  # BGR of #2b8a3e
DOTS = [(20, 24, 6), (44, 24, 6), (32, 38, 6), (14, 46, 4), (50, 46, 4)]


def draw(size, rounded=True, scale=1.0):
    img = np.zeros((size, size, 4), np.uint8)
    if rounded:
        r = int(size * 0.19)
        cv2.rectangle(img, (r, 0), (size - r - 1, size - 1), (*GREEN, 255), -1)
        cv2.rectangle(img, (0, r), (size - 1, size - r - 1), (*GREEN, 255), -1)
        for cx in (r, size - r - 1):
            for cy in (r, size - r - 1):
                cv2.circle(img, (cx, cy), r, (*GREEN, 255), -1, cv2.LINE_AA)
    else:
        img[:] = (*GREEN, 255)
    k = size / 64.0 * scale
    off = size * (1 - scale) / 2
    for x, y, rad in DOTS:
        cv2.circle(img, (int(off + x * k), int(off + y * k)), max(1, int(rad * k)), (255, 255, 255, 255), -1, cv2.LINE_AA)
    return img


def png(img):
    return cv2.imencode(".png", img)[1].tobytes()


(OUT / "icon-192.png").write_bytes(png(draw(192)))
(OUT / "icon-512.png").write_bytes(png(draw(512)))
(OUT / "icon-maskable-512.png").write_bytes(png(draw(512, rounded=False, scale=0.7)))
# iOS applies its own mask: full-bleed, opaque
(OUT / "apple-touch-icon.png").write_bytes(png(cv2.cvtColor(draw(180, rounded=False), cv2.COLOR_BGRA2BGR)))
data = png(draw(256))
(OUT / "swarm.ico").write_bytes(struct.pack("<HHH", 0, 1, 1) + struct.pack("<BBBBHHII", 0, 0, 0, 0, 1, 32, len(data), 22) + data)
print("icons written to", OUT)
