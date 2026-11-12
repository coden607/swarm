# Swarm iPhone camera management and alert reliability

## Operating architecture
Camera streams (RTSP/ONVIF/HTTP/USB/phone) → **always-on Swarm server** (local counting) → browser push / optional SMS / local siren → iPhone.

The iPhone can add any number of supported camera endpoints and configure per-camera/combined thresholds through the current web dashboard, including brand presets and auto-discovery. Proprietary cloud-only cameras without compatible RTSP/ONVIF/HTTP feeds remain unsupported. A physical server on the camera network performs ongoing detection; iOS background suspension prevents reliable 24/7 on-device multi-camera processing.

## iOS notification setup
- In Safari, visit the Swarm **HTTPS** server URL, Share → Add to Home Screen, open the new icon, tap **Enable alerts on this device**. iOS 16.4+ required.
- Do not assume a signed native IPA with WKWebView will receive Web Push: native APNs integration is a separate implementation.
- Web Push needs server/provider/phone network paths and permission. Background/locked delivery is OS-managed, not instantaneous guaranteed.

## SMS configuration (optional, can incur provider charges)
On the **always-on server**, set these private environment variables (or your existing .env with appropriate file permissions) then restart:
```text
SWARM_SMS_TWILIO_SID=<YOUR_TWILIO_ACCOUNT_SID>
SWARM_SMS_TWILIO_TOKEN=<YOUR_TWILIO_AUTH_TOKEN>
SWARM_SMS_FROM=<YOUR_OWN_E164_NUMBER>
SWARM_SMS_TO=<COMMA_SEPARATED_RECIPIENT_E164_NUMBERS>
```
Never commit real values or share them with agents. The HTTP endpoint `GET /alerts/delivery` (bearer-authenticated) reports only whether SMS is configured and how many messages await retry, without disclosing phone numbers.

## Offline matrix
| Status | Local detection | Local sound/history | iPhone push | SMS |
|---|---|---|---|---|
| Server internet and phone online | Yes | Yes | If subscribed | If configured |
| Server internet down, LAN cameras still reachable | Yes | Yes | No until restored | Queued to disk, retried later |
| iPhone disconnected but site online | Yes | Yes | Delayed by OS/provider | Cellular carrier-dependent |
| Server offline/cameras unreachable | No new counts | Old history | No new detection events | No new detection events |

The SMS outbox is **at least once**, so rare duplicate texts may occur if the provider accepts a message just before a host crash. Queue capacity is 1,000 recipients/messages; on overflow it retains prior alerts and reports failure rather than overwriting history. Messages contain a short count and label, never a camera frame.

For truly prompt delivery during *site* internet failure, add an independent cellular router/gateway on the Swarm server, and separately monitor power, server health and camera connectivity. Without any route off site, instantaneous remote alerting is physically impossible.
