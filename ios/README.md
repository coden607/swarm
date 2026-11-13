# Swarm for iPhone / iPad

iOS can't run the detection service. The iPhone is a viewer/controller: live cameras, swarm alerts, add cameras. Point it at a Swarm server (PC, Mac, Linux box, Pi or Android phone) or its public https link. Offline it shows the last known cameras and alerts.

## 1. Fastest (no Mac, no Apple ID): web app
1. In Safari open the server address (`http://<server-ip>:8000` on home Wi-Fi, or the https link).
2. Share -> **Add to Home Screen**. Open Swarm from the icon.
3. Push alerts need the **https** link and iOS 16.4+: open from the Home Screen icon, tap **Enable alerts**.

## 2. One tap, then interactive leftovers
Open [the installer](https://cdn.jsdelivr.net/gh/coden607/swarm@main/installer.html) in Safari and tap **Install Swarm**.

The page runs every step it can. When Apple or SideStore needs you, it shows one numbered card at a time (Settings → Install, SideStore confirm, Settings → Trust, or first-time SideStore with iloader on a computer). Tap **I've done this** / **I trusted Swarm** to continue. Swarm does not ask for the Apple ID password. It searches the Wi‑Fi for the server on its own.

A free Apple ID expires the app in about 7 days; opening SideStore refreshes it with the same saved login.

## 3. With a Mac (Xcode)
```sh
brew install xcodegen
cd ios && xcodegen && open Swarm.xcodeproj
```
Select your iPhone, set your Team under Signing, Run.

Unverified on a real device: the unsigned IPA is only built in CI, not tested on hardware.

## Reliable alerts
The native iOS app embeds a web view. For alerts when the phone is locked, use the HTTPS Safari Home Screen app (iOS 16.4+) and tap **Enable alerts on this device**. Native APNs is not implemented. The iPhone is not a reliable always-on detector.

On the same Wi-Fi, an open Swarm dashboard gets the alarm from the server directly. That does not need the internet. `SWARM_NTFY=1` is the free phone alarm (the ntfy app, no account, no per-message fee). A locked iPhone will not get that self-hosted topic instantly; the server speaker and an open dashboard are the instant warnings. Web Push still needs HTTPS and Apple's servers. Twilio SMS is paid and stays off unless you set it. A power cut still stops detection unless that server, the cameras, and the switch are on a battery.
