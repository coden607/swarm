# Android

1. Install **Termux** from F‑Droid: https://f-droid.org/packages/com.termux/ (not the Play Store build).
2. In Termux:

```sh
pkg install -y curl && curl -fsSL https://raw.githubusercontent.com/coden607/swarm/main/install.sh | sh
```

3. Open `http://127.0.0.1:8000` in Chrome → menu → **Add to Home Screen**.

Run `termux-wake-lock` (Termux notification) so Android doesn't kill it. Restart later with `swarm`. Uses Termux's `opencv-python`/`python-numpy` packages (no Docker, no proot).
