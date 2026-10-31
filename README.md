# Swarm Detection

Connect almost any camera, count people on each, and alert when a swarm forms - per camera or across all cameras combined. Manage everything from a dashboard that installs like an app on desktop, Android and iPhone.

## Single click
Download one file, double‑click it, done (it installs, adds a desktop icon, starts the service and opens the dashboard already signed in):
- **Windows:** [Install-Windows.bat](https://github.com/coden607/swarm/raw/main/Install-Windows.bat)
- **macOS:** [Install-Mac.command](https://github.com/coden607/swarm/raw/main/Install-Mac.command) (first time: right‑click → Open)
- **Linux:** [Install-Linux.sh](https://github.com/coden607/swarm/raw/main/Install-Linux.sh)
- **Android:** [Swarm.apk](https://github.com/coden607/swarm/releases/download/apk/Swarm.apk) — open the file to install (allow installs from your browser once). It finds your server and keeps swarm alerts on in the background. To run the server on the phone, install Termux from F‑Droid and use the one‑liner below.
- **iPhone/iPad:** works as a viewer/controller of the server (live camera view, alerts, add cameras). Open the server's **https** link in Safari → Share → Add to Home Screen → open it from the Home Screen → **Enable alerts on this device** for push notifications (iOS 16.4+). Native test app in `ios/`.

On first open with no cameras it scans your network automatically; tap a result, add the camera's login if it has one, and you're counting.
Cloud‑only cameras (Ring, Nest, Blink, Arlo without RTSP) can't be read by any local system; use the phone camera mode or a camera with RTSP/ONVIF.

## One‑line install

**Linux / macOS / Android (Termux)**
```sh
curl -fsSL https://raw.githubusercontent.com/coden607/swarm/main/install.sh | sh
```

**Windows (PowerShell)**
```powershell
irm https://raw.githubusercontent.com/coden607/swarm/main/install.ps1 | iex
```

No Docker. The installer sets up Python + dependencies, creates `.env` (random admin password), starts an auto‑restarting service, puts a **Swarm Detection icon on your Desktop / app menu / Start Menu**, and prints the URL, login and a QR code.

Add `SWARM_REMOTE=1` before the command to also get a public https link you can open from anywhere (login still required): `SWARM_REMOTE=1 curl -fsSL … | sh` / `$env:SWARM_REMOTE=1; irm … | iex`.

## Cameras it works with
Type whatever you have in **Add camera**:
- **Camera IP** (`192.168.1.20`) + optional user/password: auto‑tries ~40 common RTSP/HTTP paths (Hikvision, Dahua/Amcrest, Axis, Reolink, Tapo, Foscam, UniFi, generic ONVIF…), then asks the camera via ONVIF.
- **Full URL**: `rtsp://…`, MJPEG `http://…/video.mjpg`, single‑image snapshot URLs (`…/snapshot.jpg`).
- **USB webcam**: `0`. **Video file path**: for testing.
- **A phone/tablet/laptop browser** ("Use this device's camera"): needs https, so use the remote link or `SWARM_HTTPS=1`.
- **Scan network** finds ONVIF/RTSP devices automatically.

Cameras reconnect automatically and are remembered across restarts.

## Detection
- **Offline (default):** built‑in OpenCV person detector. No internet, no key. Works for upright people at moderate distance; very dense crowds are under‑counted.
- **Online:** add a Gemini key in `.env` for better accuracy; falls back to the offline detector automatically if the internet drops.
- Per‑camera threshold plus a **combined swarm threshold** across all cameras. Alerts: red banner, browser beep + notification, server sound, optional email. History is kept.

## Online and offline
- **On your network (no internet needed):** open `http://<server-ip>:8000` from any device.
- **From anywhere:** `SWARM_REMOTE=1` link (shown in the app), or use Tailscale.
- **If the server is unreachable**, the app still opens (cached shell) and shows the last known cameras and alerts with an OFFLINE banner.

## Apps
- **Desktop icon:** created by the installer.
- **Android app:** [Swarm.apk](https://github.com/coden607/swarm/releases/download/apk/Swarm.apk) — open the file to install.
- **Android / desktop Chrome/Edge:** open the URL → **Install app**.
- **iPhone/iPad (PWA):** Safari → Share → Add to Home Screen.
- **iPhone test app (native wrapper):** see [`ios/README.md`](ios/README.md).

## Options (env vars)
`SWARM_HOME` · `SWARM_PORT` · `GEMINI_API_KEY` · `SWARM_REMOTE=1` · `SWARM_HTTPS=1` · `SWARM_NO_START=1` · `SWARM_NO_SERVICE=1` · `SWARM_NO_ICON=1`
Detector: `SWARM_DETECTOR=auto|local|gemini`, `GEMINI_MODEL`. Uninstall (Linux/macOS/Termux): `sh install.sh --uninstall`.
Other `.env` keys: `ADMIN_USER`, `ADMIN_PASS`, `JWT_SECRET`, `EMAIL_SMTP_*`, `EMAIL_FROM`, `ONVIF_USER`/`ONVIF_PASS`.

## API (Bearer token from `POST /login`)
`GET /status` · `GET /events` · `GET/POST/DELETE /cameras[/{id}]` · `PUT /cameras/{id}/threshold` · `PUT /settings` · `GET /discover` · `GET /remote` · `POST /cameras/{id}/frame` · `GET /health`

Camera passwords are stored in `data/cameras.json` (permissions 600). Keep `.env` and `data/` private.
