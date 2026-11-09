from __future__ import annotations

import logging
import os
import socket

# Optional ONVIF support – will be used if the user installs `onvif-zeep`
try:
    from onvif import ONVIFCamera  # type: ignore
    ONVIF_AVAILABLE = True
except Exception:  # pragma: no cover
    ONVIF_AVAILABLE = False

def _port_open(host: str, port: int, timeout: float = 0.4) -> bool:
    try:
        with socket.create_connection((host, port), timeout):
            return True
    except OSError:
        return False


def _discover_onvif_rtsp(host: str, user: str | None = None, passwd: str | None = None) -> str | None:
    """Ask the camera for its RTSP URI. Tries the usual ONVIF ports. No cloud."""
    if not ONVIF_AVAILABLE:
        return None
    user = user or os.getenv("ONVIF_USER", "admin")
    passwd = passwd or os.getenv("ONVIF_PASS", "admin")
    host = (host or "").split(":")[0]
    for port in (80, 8000, 8080, 8899):
        if not _port_open(host, port):
            continue
        try:
            cam = ONVIFCamera(host, port, user, passwd)
            media = cam.create_media_service()
            profiles = media.GetProfiles()
            req = media.create_type("GetStreamUri")
            req.ProfileToken = profiles[0].token
            req.StreamSetup = {"Stream": "RTP-Unicast", "Transport": {"Protocol": "RTSP"}}
            return media.GetStreamUri(req).Uri
        except Exception:
            continue
    logging.info("ONVIF discovery failed for %s", host)
    return None


def get_stream_capture(url: str, brand: str):
    """Open a brand-priority stream. Returns the live source, or None."""
    try:
        from .sources import open_first
        src, _resolved = open_first(url, os.getenv("ONVIF_USER", ""), os.getenv("ONVIF_PASS", ""), brand)
        return src
    except Exception as e:
        logging.error("Error initializing stream for %s (brand=%s): %s", url, brand, e)
        return None
