# Android

## A. Phone as a viewer (most people: no Termux)
**Native app:** GitHub -> Actions -> latest `ci` run -> artifact **Swarm-apk** -> unzip, open `Swarm.apk` on the phone (allow "install unknown apps"), enter the server address. It finds your server automatically. After you sign in once it keeps watching in the background and sends a phone notification when a swarm starts, even with the app closed or after a reboot (gear button -> Background alerts ON/OFF).

**Or Chrome web app:**
A computer, mini PC or Pi at home already runs Swarm.
1. In Chrome open the server's **https** link (or `http://<ip>:8000` on home Wi‑Fi).
2. Menu → **Install app**. Open Swarm from the new home‑screen icon.
3. Tap **Enable alerts on this device** (needs the https link). You get live camera views and swarm alerts, and can add cameras.

## B. Phone as the server (Termux)
1. Install **Termux** from F‑Droid: https://f-droid.org/packages/com.termux/ (not the Play Store build).
2. In Termux, paste:

```sh
pkg upgrade -y -o Dpkg::Options::=--force-confold && pkg install -y curl && curl -fsSL https://raw.githubusercontent.com/coden607/swarm/main/install.sh | sh
```

3. It prints the address and admin password and opens the dashboard. In Chrome: menu → **Install app**.

Keep it running: pull down the Termux notification and tap **Acquire wakelock**, and exclude Termux from battery optimization. Install **Termux:Boot** (F‑Droid) to auto‑start after a reboot, and **Termux:Widget** for a home‑screen shortcut named *Swarm* (the installer creates both scripts). Restart manually with `swarm`.

The phone's own camera can also be added from the dashboard ("Use this device's camera", needs the https link).
Uses Termux's `opencv-python`/`python-numpy` packages (no Docker, no proot). Phone push alerts may be unavailable in mode B if `pywebpush` can't build on your device; use mode A on a second phone for alerts.
