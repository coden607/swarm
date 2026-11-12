# Swarm for iPhone / iPad

iOS can't run the detection service. The iPhone is a viewer/controller: live cameras, swarm alerts, add cameras. Point it at a Swarm server (PC, Mac, Linux box, Pi or Android phone) or its public https link. Offline it shows the last known cameras and alerts.

## 1. Fastest (no Mac, no Apple ID): web app
1. In Safari open the server address (`http://<server-ip>:8000` on home Wi-Fi, or the https link).
2. Share -> **Add to Home Screen**. Open Swarm from the icon.
3. Push alerts need the **https** link and iOS 16.4+: open from the Home Screen icon, tap **Enable alerts**.

## 2. Native app
Open [the installer](https://cdn.jsdelivr.net/gh/coden607/swarm@main/installer.html) in Safari. Tap **Continue with this iPhone's Apple ID**. SideStore opens and signs Swarm with the Apple ID already saved in SideStore. If SideStore asks you to sign in, use the same Apple ID this phone uses. Swarm does not ask for the password.

When you come back to Safari, the page shows the one step Apple will not automate: Settings → General → VPN & Device Management → Trust. Then open Swarm. It searches the Wi‑Fi for the server on its own.

SideStore has to be installed once ([sidestore.io](https://sidestore.io)). AltStore works the same way if that is where this Apple ID is already signed in. A free Apple ID expires the app in about 7 days; opening SideStore or AltStore refreshes it with that saved login.

## 3. With a Mac (Xcode)
```sh
brew install xcodegen
cd ios && xcodegen && open Swarm.xcodeproj
```
Select your iPhone, set your Team under Signing, Run.

Unverified on a real device: the unsigned IPA is only built in CI, not tested on hardware.

## Reliable alerts
The native iOS app currently embeds WKWebView. For alerts when closed or locked, use the **HTTPS Safari Home Screen PWA** (iOS 16.4+) and tap **Enable alerts on this device**. Native APNs is not implemented. Multi-brand camera setup is handled by the existing server dashboard; iPhone is not a reliable always-on detector under iOS background execution limits.

An optional server-side Twilio SMS channel is configured using `SWARM_SMS_TWILIO_SID`, `SWARM_SMS_TWILIO_TOKEN`, `SWARM_SMS_FROM`, `SWARM_SMS_TO`. No SMS will send without all four values. Outgoing messages use a persistent local SQLite retry queue, which resumes after internet outages. The site must have a working internet/cellular uplink to actually deliver SMS or push; without any connection only local alarms and history are available.
