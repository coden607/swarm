import os


def health_check() -> dict:
    return {
        "status": "ok",
        "gemini_key_set": bool(os.getenv("GEMINI_API_KEY")),
        "detector": os.getenv("SWARM_DETECTOR", "auto"),
        "offline_ok": True,
        "confirm_hits": int(os.getenv("SWARM_CONFIRM_HITS", "3")),
    }
