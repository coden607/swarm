# Swarm alerts when the network or the power fails

Camera streams stay on the Swarm server. The server counts locally. The iPhone is a viewer.

## What is immediate
- The server siren, if `SWARM_SERVER_SOUND` is on (the default).
- Any dashboard already open on the same LAN. It listens on `GET /alerts/live`. That stream never leaves the building.
- `SWARM_LOCAL_HOOK`, a local program started with the alert text as one argument. No shell. Use it for a siren relay or an MQTT command on the LAN.

## What waits for an uplink
Web Push, email, and optional Twilio SMS are written locally and retried. Web Push retries live in `data/push-outbox.json`. SMS retries live in `data/sms-outbox.sqlite3`. `GET /alerts/delivery` reports only whether SMS is configured, how many SMS and Web Push messages are waiting, and whether the local siren and hook are enabled. It does not return phone numbers or message text.

SMS is off until all four are set: `SWARM_SMS_TWILIO_SID`, `SWARM_SMS_TWILIO_TOKEN`, `SWARM_SMS_FROM`, `SWARM_SMS_TO`. Values are E.164 (`+15551212`). The SMS queue is at least once, capped at 1,000, and stores a short count and label, never a frame.

## What a power cut does
If the Swarm computer loses power, counting stops. Put the computer, the cameras, and the switch on a battery if the alarm has to survive a blackout. A phone away from home still needs a way off the site. A cellular router on that same battery is the way to deliver SMS or Web Push while the home internet is down. No software path can notify that phone when the site has neither power nor any uplink.

## iPhone setup
Safari, the HTTPS server URL, Share → Add to Home Screen, open the icon, tap **Enable alerts on this device**. iOS 16.4+. The native WKWebView app is not a Home Screen Web Push app. iOS will not run the detector reliably in the background.
