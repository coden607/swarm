import os
import subprocess
from typing import List
from pydub import AudioSegment
from pydub.playback import play
import smtplib
from email.message import EmailMessage

# ----------------------------------------------------------------------
# Alarm sound (local)
# ----------------------------------------------------------------------
ALARM_WAV = os.getenv("ALARM_WAV_PATH", "/app/alarm.wav")

def play_alarm(sound_path: str = ALARM_WAV) -> None:
    """Play a local alarm sound file using pydub.
    The function runs synchronously; callers may wrap it in a subprocess
    if they need non‑blocking behaviour.
    """
    if not os.path.isfile(sound_path):
        print(f"[alert] Alarm file missing: {sound_path}")
        return
    try:
        audio = AudioSegment.from_file(sound_path)
        play(audio)
    except Exception as e:
        print(f"[alert] Failed to play alarm: {e}")

# ----------------------------------------------------------------------
# Email notification (fallback for phone alerts)
# ----------------------------------------------------------------------
SMTP_SERVER = os.getenv("EMAIL_SMTP_SERVER")
SMTP_PORT = int(os.getenv("EMAIL_SMTP_PORT", "587"))
SMTP_USER = os.getenv("EMAIL_SMTP_USER")
SMTP_PASS = os.getenv("EMAIL_SMTP_PASS")
EMAIL_FROM = os.getenv("EMAIL_FROM")

def send_email(to_addresses: List[str], subject: str, body: str) -> None:
    if not all([SMTP_SERVER, SMTP_USER, SMTP_PASS, EMAIL_FROM]):
        print("[alert] Email environment not fully configured – skipping email alert")
        return
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = EMAIL_FROM
    msg["To"] = ", ".join(to_addresses)
    msg.set_content(body)
    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASS)
            server.send_message(msg)
        print(f"[alert] Email sent to {to_addresses}")
    except Exception as e:
        print(f"[alert] Failed to send email: {e}")

def trigger_alert(count: int, email_addresses: List[str]) -> None:
    """Play the alarm and optionally send an email notification.
    `email_addresses` can be empty – the function will still play the alarm.
    """
    msg = f"Alert! Detected {count} people in the monitored area."
    print(f"[alert] {msg}")
    # Play sound in a subprocess to avoid blocking the detector loop
    subprocess.Popen(["python", "-c", f"import app.alert as a; a.play_alarm()"])
    if email_addresses:
        subprocess.Popen([
            "python",
            "-c",
            f"import app.alert as a; a.send_email({email_addresses!r}, 'Swarm Alert', '{msg}')",
        ])
