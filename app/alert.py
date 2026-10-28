import os
import smtplib
import subprocess
import sys
import wave
from email.message import EmailMessage
from pathlib import Path
from typing import List

from . import events, push

_ROOT = Path(__file__).resolve().parent.parent
_DATA = Path(os.getenv("SWARM_DATA_DIR", _ROOT / "data"))
ALARM_WAV = os.getenv("ALARM_WAV_PATH", str(_DATA / "alarm.wav"))


def ensure_alarm(path: str = ALARM_WAV) -> None:
    """Generate a default two-tone alarm if none exists (stdlib only)."""
    if os.path.isfile(path):
        return
    import math
    import struct
    os.makedirs(os.path.dirname(path), exist_ok=True)
    rate = 22050
    frames = b"".join(
        struct.pack("<h", int(12000 * math.sin(2 * math.pi * (880 if (i // 5000) % 2 else 660) * i / rate)))
        for i in range(rate * 2)
    )
    with wave.open(path, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(rate); w.writeframes(frames)


def play_alarm(sound_path: str = ALARM_WAV) -> None:
    """Server-side sound (best effort; the web UI also beeps in the browser)."""
    try:
        ensure_alarm(sound_path)
        from pydub import AudioSegment  # lazy: audio stack must never block startup
        from pydub.playback import play
        play(AudioSegment.from_file(sound_path))
    except Exception as e:
        print(f"[alert] server alarm unavailable: {e}")


SMTP_SERVER = os.getenv("EMAIL_SMTP_SERVER")
SMTP_PORT = int(os.getenv("EMAIL_SMTP_PORT", "587"))
SMTP_USER = os.getenv("EMAIL_SMTP_USER")
SMTP_PASS = os.getenv("EMAIL_SMTP_PASS")
EMAIL_FROM = os.getenv("EMAIL_FROM")


def send_email(to_addresses: List[str], subject: str, body: str) -> None:
    if not all([SMTP_SERVER, SMTP_USER, SMTP_PASS, EMAIL_FROM]):
        print("[alert] Email not configured - skipping")
        return
    msg = EmailMessage()
    msg["Subject"], msg["From"], msg["To"] = subject, EMAIL_FROM, ", ".join(to_addresses)
    msg.set_content(body)
    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as s:
            s.starttls()
            s.login(SMTP_USER, SMTP_PASS)
            s.send_message(msg)
        print(f"[alert] Email sent to {to_addresses}")
    except Exception as e:
        print(f"[alert] Failed to send email: {e}")


def trigger_alert(count: int, email_addresses: List[str], label: str = "") -> None:
    msg = f"Swarm alert{' on ' + label if label else ''}: {count} people detected."
    print(f"[alert] {msg}")
    events.add(label, count)
    push.send_async("Swarm alert", msg)
    if os.getenv("SWARM_SERVER_SOUND", "1") == "1":
        subprocess.Popen([sys.executable, "-c", "import app.alert as a; a.play_alarm()"], cwd=str(_ROOT))
    if email_addresses:
        subprocess.Popen([sys.executable, "-c",
                          f"import app.alert as a; a.send_email({list(email_addresses)!r}, 'Swarm Alert', {msg!r})"], cwd=str(_ROOT))
