import cv2
import logging
import socket
from urllib.parse import urlparse

# Optional ONVIF support – will be used if the user installs `onvif-zeep`
try:
    from onvif import ONVIFCamera  # type: ignore
    ONVIF_AVAILABLE = True
except Exception:  # pragma: no cover
    ONVIF_AVAILABLE = False

def _discover_onvif_rtsp(host: str) -> str | None:
    """Attempt to discover an ONVIF camera’s RTSP stream.
    Returns the RTSP URI or ``None`` if discovery fails.
    """
    if not ONVIF_AVAILABLE:
        return None
    try:
        # The default ONVIF ports are 80 (HTTP) and 443 (HTTPS).
        # Users can supply credentials via environment variables if needed.
        user = os.getenv("ONVIF_USER", "admin")
        passwd = os.getenv("ONVIF_PASS", "admin")
        cam = ONVIFCamera(host, 80, user, passwd)
        media_service = cam.create_media_service()
        profiles = media_service.GetProfiles()
        # Use the first profile – most cameras expose a single stream.
        token = profiles[0].token
        req = media_service.create_type("GetStreamUri")
        req.ProfileToken = token
        req.StreamSetup = {
            "Stream": "RTP-Unicast",
            "Transport": {"Protocol": "RTSP"},
        }
        uri = media_service.GetStreamUri(req).Uri
        return uri
    except Exception as e:
        logging.warning(f"ONVIF discovery failed for {host}: {e}")
        return None

def get_stream_capture(url: str, brand: str):
    """Return a ``cv2.VideoCapture`` appropriate for the camera brand.
    The function tries brand‑specific handling first; if that fails it falls
    back to a generic RTSP/HTTP stream.
    """
    try:
        if brand.lower() == "generic":
            return cv2.VideoCapture(url)
        # ONVIF – we try to discover the real RTSP link from the device IP.
        if brand.lower() == "onvif":
            parsed = urlparse(url)
            host = parsed.hostname or url
            rtsp_uri = _discover_onvif_rtsp(host)
            if rtsp_uri:
                return cv2.VideoCapture(rtsp_uri)
            # Fallback to the provided URL if discovery fails.
            return cv2.VideoCapture(url)
        # Add placeholder branches for other brands.
        # Future implementations can import vendor SDKs here.
        logging.info(f"Brand '{brand}' not yet implemented – using generic stream.")
        return cv2.VideoCapture(url)
    except Exception as e:
        logging.error(f"Error initializing stream for {url} (brand={brand}): {e}")
        return None
