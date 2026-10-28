# iPhone as the server (iSH) - experimental

iSH runs Alpine Linux on an emulated CPU, so detection is slow (a few seconds per frame) and iOS pauses iSH in the background. Use it for trying Swarm; for real use run the server on a PC, Pi or Android phone and use the iPhone as the viewer.

1. Install **iSH** from the App Store.
2. Open iSH and paste:

```sh
apk add curl && curl -fsSL https://raw.githubusercontent.com/coden607/swarm/main/install.sh | sh
```

3. Open `http://127.0.0.1:8000` in Safari (the installer prints the address and admin password), then Share -> Add to Home Screen.
4. Keep iSH open (Settings -> Background location trick in iSH keeps it alive). Restart with `swarm`.

Unverified on a real iPhone. CI only tests the Alpine package path on x86_64.
