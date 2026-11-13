# Swarm alerts when the network or the power fails

Camera streams stay on the Swarm server. The server counts locally. The iPhone is a viewer.

## What is immediate
- The server siren, if `SWARM_SERVER_SOUND` is on (the default).
- Any dashboard already open on the same LAN. It listens on `GET /alerts/live`. That stream never leaves the building.
- `SWARM_LOCAL_HOOK`, a local program started with the alert text as one argument. No shell. Use it for a siren relay or an MQTT command on the LAN.

## What waits for an uplink
Web Push and email are written locally and retried. Web Push retries live in `data/push-outbox.json`. Twilio SMS is paid, so leave it unset. `GET /alerts/delivery` reports whether SMS is configured, how many messages are waiting, whether the local siren and hook are enabled, and the free ntfy subscribe address. It does not return phone numbers or message text.

## Free phone alarm
`SWARM_NTFY=1` posts the same short count to a ntfy server on this machine (`http://127.0.0.1:2586` unless `SWARM_NTFY_URL` is set). The phone app subscribes to the LAN address from the dashboard. There is no account and no per-alert fee. Android on this Wi-Fi gets it immediately, including when the internet is down. An iPhone gets an instant beep from the server speaker and from an open dashboard. Self-hosted ntfy cannot ring a locked iPhone in the background; that needs Apple's push service. Paid Twilio SMS stays available only if all four `SWARM_SMS_*` values are set.

## What a power cut does
If the Swarm computer loses power, counting stops. Put the computer, the cameras, and the switch on a battery if the alarm has to survive a blackout. A phone away from home still needs a way off the site. A cellular router on that same battery is the way to deliver SMS or Web Push while the home internet is down. No software path can notify that phone when the site has neither power nor any uplink.

## iPhone setup
Safari, the HTTPS server URL, Share → Add to Home Screen, open the icon, tap **Enable alerts on this device**. iOS 16.4+. The native WKWebView app is not a Home Screen Web Push app. iOS will not run the detector reliably in the background.
