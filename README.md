# Swarm Detection Service

## One‑Click Installation Guide

### Android
- Use the **One‑Click Installer** page (`installer.html`). It detects Android and offers a button that installs **Termux** from F‑Droid and runs a bootstrap script (`setup_swarm.sh`) which sets up a proot Alpine distro, installs Docker, pulls the Swarm repo and runs `install.sh`.

### iOS (iPhone / iPad)
- iOS cannot run Docker locally. Instead, run the service on a reachable Linux host (your VPS, a desktop, or the Android Termux environment) and access the UI as a **Progressive Web App (PWA)**.
- Open Safari on your iPhone and navigate to the URL provided by the installer page (e.g., `https://YOUR_HOST_DOMAIN_OR_IP`).
- Tap **Share** → **Add to Home Screen**. This creates a one‑tap app icon that launches the Swarm UI.
- The UI works offline after the first load and provides the same wizard for adding cameras of any brand.

### Desktop (Windows / macOS / Linux)
- Click the **Download & Run Installer** button on the installer page. It downloads `install.sh`; make it executable (`chmod +x install.sh`) and run with `sudo`.
- The script installs Docker, builds the container, sets up a `systemd` service, and generates a QR code for mobile access.

### All Platforms
- After installation, ensure port **8000** (or HTTPS 443 if you enable Caddy) is reachable from your mobile device.
- The service automatically restarts on failure via the systemd watchdog.

---

For detailed troubleshooting, see the `android/README.md` and the **FAQ** section below.

A private repository that connects to arbitrary camera streams, detects swarms of people using the Gemini model, and triggers alerts (sound alarm or phone calls) when the number of people exceeds a configurable threshold.

## Features
- Connect to any RTSP/HTTP camera URL.
- Configurable swarm size threshold.
- Gemini model (`gemini-pro`) for person count inference.
- Alerts:
  - Local alarm sound.
  - Optional Twilio phone call notifications.
- FastAPI HTTP API for managing cameras and thresholds.
- Docker support.
